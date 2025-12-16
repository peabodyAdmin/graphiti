# Phase 5 Foundation

## Introduction
This document defines the Phase 5 domain model for Aiden’s data-driven, composable, and recursive architecture. It establishes **what entities exist** and **what mutations are valid** without prescribing implementation details. Phase 5 replaces hardcoded context logic with three core concepts:

- **Service (where work happens):** A metadata hub describing every infrastructure endpoint the platform can reach.
- **Tool (what work to perform):** A reusable operation definition bound to a Service, complete with input/output schemas.
- **Process (how work is orchestrated):** A data-defined workflow that sequences Tools (and other Processes) to assemble context, manage memory, or fulfill any internal job.

Together these concepts ensure every behavior is configured, versioned, and observable in data—not embedded in code.

---

## Entities

### Service
**Purpose**
- Describes an infrastructure endpoint type and defines the schema/template for connection parameters. Services are configuration templates that Tools instantiate.

**State**
- `id` (string, immutable)
- `name` (string, mutable)
- `type` (enum: `neo4j_graph`, `rest_api`, `llm_provider`, `mcp_server`; immutable)
- `connectionSchema` (JSON Schema object defining required/optional connection parameters)
- `protocol` (`bolt` | `bolt+s` | `http` | `https` | `stdio` | `sse`; immutable)
- `requiresSecret` (boolean, immutable)
- `enabled` (boolean, mutable)
- `status` (`healthy` | `degraded` | `down`; system-managed)
- `lastHealthCheck`, `errorMessage`, `createdAt`, `updatedAt`
- `shared` (boolean, default `false`, mutable; governs discoverability by non-owners)
- `serviceTemplateId` (string reference, nullable, immutable if present)
  **Semantics:** Audit trail only. Records which template this Service was instantiated from. 
  NOT an operational dependency—Service contains complete copied structure and functions 
  independently whether template exists or is archived. Soft reference may point to archived template.

**Valid Mutations**
- **Create:** Provide type, protocol, and connectionSchema defining parameter shape; establish `OWNED_BY` edge from auth context; optionally originate from `serviceTemplateId`.
- **Update:** May adjust name, enabled flag, schema (with version increment); status updated via health checks.
- **Delete:** Allowed only when no Tools reference the Service.

**Invariants**
- Type and protocol combinations must match (e.g., `neo4j_graph` requires `bolt` or `bolt+s`).
- `connectionSchema` must be valid JSON Schema.
- Services with `requiresSecret=true` mandate that Tools create `USES_SECRET` edges to vault-backed Secrets.
- Disabled Services cannot report `status = healthy`.
- If Service uses a Secret, Secret ownership MUST match the Service owner (enforced via `OWNED_BY` edges; Secrets are never cross-user).
- Cross-owner references require sharing: Tool and Service owners differ → Service.shared MUST be true.

**Relationships**
- `Service --OWNED_BY--> User` (`created_at`)

**Edge Constraints**
- `OWNED_BY` target: Immutable after creation. Ownership cannot transfer.

**Examples**

Neo4j Service connectionSchema:
```json
{
  "type": "object",
  "required": ["endpoint", "database"],
  "properties": {
    "endpoint": {"type": "string", "format": "uri"},
    "database": {"type": "string"},
    "maxConnectionPoolSize": {"type": "integer", "default": 50}
  }
}
```

LLM Provider Service connectionSchema:
```json
{
  "type": "object",
  "required": ["endpoint", "model"],
  "properties": {
    "endpoint": {"type": "string", "format": "uri"},
    "model": {"type": "string"},
    "temperature": {"type": "number", "minimum": 0, "maximum": 2, "default": 0.7},
    "maxTokens": {"type": "integer", "minimum": 1}
  }
}
```

---

### Secret
**Purpose**
- Holds encrypted credentials referenced by Services without ever exposing plaintext values.

**State**
- `id` (string, immutable)
- `name` (string, mutable)
- `type` (`api_key`, `oauth_token`, `password`, `certificate`; immutable)
- `encryptedValue` (opaque blob, immutable once written)
- `createdAt`, `updatedAt`
- `shared` (boolean, default `false`, mutable; Secrets remain owner-only even if set true)

**Valid Mutations**
- **Create:** Store encrypted payload and metadata; establish `OWNED_BY` edge from auth context and never change ownership.
- **Update:** Rotate `encryptedValue`, rename, or change metadata without altering `id`.
- **Delete:** Allowed only when no Service currently `USES` it.

**Invariants**
- `encryptedValue` never leaves storage unredacted.
- Ownership is immutable; all Secret reads/writes are filtered to the owning User.
- Secret references (Service/Tool usage) MUST match the same owner; cross-user access returns 404.
- Secrets cannot be cross-user shared for execution; `shared` flag does not grant access beyond owner.
- Each Secret can be referenced by multiple Services but remains scoped per user.

**Relationships**
- `Tool --USES_SECRET--> Secret` (`scope`; credentials remain vaulted)
- `Secret --OWNED_BY--> User` (`created_at`)

**Edge Constraints**
- `OWNED_BY` target: Immutable after creation. Ownership cannot transfer.

**References**
- `USES_SECRET` edges from Tools authorize access. Execution validates the Secret belongs to the same user as the Conversation.

---

### Tool
**Purpose**
- Defines a single executable operation against a Service, providing concrete connection parameters that populate the Service's connectionSchema.

**State**
- `id` (string, immutable)
- `name` (string, mutable)
- `connectionParams` (object conforming to Service.connectionSchema; credentials supplied via `USES_SECRET` edge when required)
- `operation` (discriminated union by Service type)
- `inputSchema` (JSON Schema for operation inputs)
- `outputSchema` (JSON Schema for operation outputs)
- `enabled` (boolean, mutable)
- `status` (`healthy` | `degraded` | `down`; system-managed) 
- `lastHealthCheck` (timestamp, system-managed)             
- `errorMessage` (string, nullable, system-managed)       
- `createdAt`, `updatedAt`
- `shared` (boolean, default `false`, mutable; discoverability for non-owners)
- `toolTemplateId` (string reference, nullable, immutable if present)
  **Semantics:** Audit trail only. Records which template this Tool was instantiated from. 
  NOT an operational dependency—Tool contains complete copied structure and functions 
  independently whether template exists or is archived. Soft reference may point to archived template.

**Valid Mutations**
- **Create:** Bind operation + schemas + connectionParams to existing Service; establish `OWNED_BY`, `USES_SERVICE`, and `USES_SECRET` (if required) edges; optionally originate from `toolTemplateId`.
- **Update:** Change description, schemas, operation parameters, or enabled flag.
- **Delete:** Allowed only when no ProcessSteps reference the Tool.

**Invariants**
- `connectionParams` must validate against Service `connectionSchema`.
- If Service has `requiresSecret=true`, Tool must create `USES_SECRET` edge to a valid Secret.
- Cross-owner Service reference requires `Service.shared=true`; otherwise reject (enforced alongside `USES_SERVICE` edge).
- Operation type must align with Service type.
- `inputSchema` keys must match variable names used inside `operation` definitions.

**Relationships**
- `Tool --OWNED_BY--> User` (`created_at`)
- `Tool --USES_SERVICE--> Service` (`connectionParams`; connection parameters carried on the edge)
- `Tool --USES_SECRET--> Secret` (`scope`; credentials stay in vault, not the graph)

**Edge Constraints**
- `OWNED_BY` target: Immutable after creation.
- `USES_SERVICE` target: Immutable after creation; Service binding fixed at Tool creation.
- `USES_SERVICE.connectionParams`: Mutable; connection configuration may be updated.
- `USES_SECRET` target: Mutable; Secret can be rotated to a new Secret node.

**Example**

Tool for specific Neo4j instance:
```json
{
  "connectionParams": {
    "endpoint": "bolt://localhost:7687",
    "database": "graphiti",
    "maxConnectionPoolSize": 100
  },
  "operation": {
    "type": "graph_query",
    "query": "MATCH (n:Entity) WHERE n.name = $name RETURN n"
  }
}
```
Edges: `USES_SERVICE -> service-neo4j-graphiti`, `USES_SECRET -> secret-neo4j-prod-creds`, `OWNED_BY -> user-123`.

Tool for specific LLM endpoint:
```json
{
  "connectionParams": {
    "endpoint": "https://api.anthropic.com",
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "maxTokens": 4096
  },
  "operation": {
    "type": "llm_call",
    "systemPrompt": "You are a helpful assistant.",
    "promptTemplate": "{{instruction}}\n\n{{content}}"
  }
}
```
Edges: `USES_SERVICE -> service-anthropic-claude`, `USES_SECRET -> secret-anthropic-api-key`, `OWNED_BY -> user-123`.

---

### ServiceTemplate
**Purpose**
- Immutable blueprint for creating Services with predefined type/protocol/connectionSchema.

**State**
- `id` (string, immutable)
- `ownerId` (string, immutable; set from auth context)
- `name` (string, immutable)
- `description` (string, immutable, nullable)
- `type` (enum: `neo4j_graph`, `rest_api`, `llm_provider`, `mcp_server`; immutable)
- `protocol` (`bolt` | `bolt+s` | `http` | `https` | `stdio` | `sse`; immutable)
- `connectionSchema` (JSON Schema object defining required/optional connection parameters; immutable)
- `requiresSecret` (boolean, immutable)
- `shared` (boolean, default `false`, mutable)
- `archived` (boolean, default `false`, mutable)
  Soft delete flag. Archived templates excluded from default listings but remain accessible via direct GET and ?includeArchived=true filter. Preserves audit trail and maintains referential integrity for instance serviceTemplateId fields.
- `createdAt`, `updatedAt`

**Instantiation Semantics (Denormalized Data, Audit Reference)**

When a Service is created from a ServiceTemplate:
1. Service receives complete copy of all structural fields (type, protocol, connectionSchema, requiresSecret)
2. Service.serviceTemplateId set to template UUID (immutable audit field)
3. Template and Service are operationally independent from that moment
4. Template changes NEVER affect existing Services
5. Template archival/deletion NEVER affects existing Services
6. Service.serviceTemplateId preserved for provenance even if template archived

**Provenance vs. Dependency:**
- `serviceTemplateId` is provenance (audit trail), NOT operational dependency
- Services function identically whether referenced template exists or is archived
- UI may display "(template archived)" for archived templates, but Service remains fully functional

**Valid Mutations**
- **Create:** Define immutable template structure; capture `ownerId` from auth context.
- **Update:** Only name, description, and `shared` may change; structural fields are immutable.
- **Delete:** Allowed anytime; Services instantiated remain fully functional (template is provenance-only).

**Invariants**
- Template structure fields are immutable; sharing controls discoverability for other users.

---

### ToolTemplate
**Purpose**
- Immutable blueprint for creating Tools with predefined operation/input/output schemas.

**State**
- `id` (string, immutable)
- `ownerId` (string, immutable; set from auth context)
- `name` (string, immutable)
- `description` (string, immutable, nullable)
- `operation` (immutable)
- `inputSchema` (immutable)
- `outputSchema` (immutable)
- `shared` (boolean, default `false`, mutable)
- `archived` (boolean, default `false`, mutable)
  Soft delete flag. Archived templates excluded from default listings but remain accessible via direct GET and ?includeArchived=true filter. Preserves audit trail and maintains referential integrity for instance toolTemplateId fields.
- `createdAt`, `updatedAt`

**Instantiation Semantics (Denormalized Data, Audit Reference)**

When a Tool is created from a ToolTemplate:
1. Tool receives complete copy of all structural fields (operation, inputSchema, outputSchema)
2. Tool.toolTemplateId set to template UUID (immutable audit field)
3. Template and Tool are operationally independent from that moment
4. Template changes NEVER affect existing Tools
5. Template archival/deletion NEVER affects existing Tools
6. Tool.toolTemplateId preserved for provenance even if template archived

**Provenance vs. Dependency:**
- `toolTemplateId` is provenance (audit trail), NOT operational dependency
- Tools function identically whether referenced template exists or is archived
- UI may display "(template archived)" for archived templates, but Tool remains fully functional

**Valid Mutations**
- **Create:** Define immutable tool blueprint; capture `ownerId` from auth context.
- **Update:** Only name, description, and `shared` may change; operation/schema remain immutable.
- **Delete:** Allowed anytime; Tools instantiated remain fully functional (template is provenance-only).

**Invariants**
- Template structure fields are immutable; sharing controls discoverability for other users.

---

**Sharing Model Note**
- ServiceTemplate and ToolTemplate carry `ownerId` and `shared` properties with unified semantics: default private (`shared=false`), optionally discoverable when `shared=true`.
- Service, Tool, and Secret express ownership via `OWNED_BY` edges and use `shared` flags where applicable. Secrets remain owner-only even if marked shared; cross-user Secret execution is prohibited.
```

---

### Process
**Purpose**
- Orchestrates multiple Tools into a reusable workflow for context assembly, maintenance, or delegation.

**State**
- `id`, `name`, `description`
- `initialContext` (list of required input variable names)
- `steps` (ordered collection of ProcessStep documents)
- `outputTemplate` (Handlebars-style string)
- `tokenBudget` (number, optional)
- `maxRecursionDepth` (integer)
- `enabled` (boolean)
- `createdAt`, `updatedAt`

**Valid Mutations**
- **Create:** Define name, context requirements, steps, and template.
- **Update:** Replace steps, templates, or budgets; toggle enabled flag.
- **Delete:** Allowed only when no Conversations reference it.

**Invariants**
- Must contain at least one ProcessStep.
- Step dependencies within a Process cannot form cycles.
- Every variable referenced in `outputTemplate` must originate from `initialContext` or step outputs.

**Relationships**
- `Process --OWNED_BY--> User` (`created_at`)
- Defined via ordered `steps`; ProcessSteps connect to Tools/Processes using `CALLS_TOOL` / `CALLS_PROCESS` edges.
- Conversations link preferred Processes via `DEFAULT_PROCESS` edges.

**Edge Constraints**
- `OWNED_BY` target: Immutable after creation. Ownership cannot transfer.

**References**
- Conversations store Process preference through `DEFAULT_PROCESS` edge.
- ProcessSteps drive recursive execution; `CALLS_PROCESS` edges must stay within `maxRecursionDepth`.

---

### ProcessStep
**Purpose**
- Represents one unit of work inside a Process, defined as part of the Process specification. Includes variable bindings, execution mode, and failure policy.

**State**
- `id` (string, unique per Process)
- `inputs` (map of parameter → interpolation expression)
- `output.variable` (string)
- `output.tokenBudget` (number, optional)
- `output.required` (boolean)
- `execution.mode` (`parallel` | `sequential`)
- `execution.condition` (string expression, optional)
- `execution.timeout` (number, optional)
- `execution.interactionMode` ('auto' | 'manual')

**Valid Mutations**
- Defined by mutating the parent Process; individual steps aren’t mutated independently.

**Invariants**
- `inputs` must match the requirements of the referenced Tool or Process.
- `DEPENDS_ON` edges cannot reference the step itself or form cycles; parallel steps cannot depend on each other.
- `DEPENDS_ON` edges cannot target a step that is not mentioned prior to the dependant in the Process.
- Exactly one of `CALLS_TOOL` or `CALLS_PROCESS` MUST be specified.
- `CALLS_TOOL` target must be an enabled Tool whose Service is healthy when executed; inputs must satisfy target Tool `inputSchema` specifications.
- `CALLS_PROCESS` target must be an enabled Process within recursion limits; inputs must satisfy target Process `initialContext` variables.
- Recursive Process invocation counts toward `maxRecursionDepth`.

**Relationships**
- `ProcessStep --CALLS_TOOL--> Tool` (`timeout`, `interactionMode`)
- `ProcessStep --CALLS_PROCESS--> Process` (`timeout`)
- `ProcessStep --DEPENDS_ON--> ProcessStep` (`order`; captures sequencing + dependency graph)

**Edge Constraints**
- `CALLS_TOOL` target: Immutable. Defined as part of Process specification.
- `CALLS_PROCESS` target: Immutable. Defined as part of Process specification.
- `CALLS_TOOL.timeout`, `CALLS_TOOL.interactionMode`: Immutable. Part of step definition.
- `CALLS_PROCESS.timeout`: Immutable. Part of step definition.
- `DEPENDS_ON` edge set: Immutable. Dependency graph fixed at Process creation.
- `DEPENDS_ON.order`: Immutable. Execution sequencing.
- Exactly one of `CALLS_TOOL` or `CALLS_PROCESS` must exist (cardinality constraint).

**References**
- `CALLS_TOOL` / `CALLS_PROCESS` edges identify the invocation target.
- `DEPENDS_ON` edges capture execution ordering and gating.
- Target validation: referenced Tool/Process must be enabled and healthy before execution

For LLM Tools, the same `inputs` map supplies the values that fill the Tool’s prompt template. Variable interpolation happens at execution time so prompts can adapt to prior step outputs.

**Execution Model:**
- ProcessStep execution is the atomic unit of work in the system.
- Each ProcessStep corresponds to exactly one Worker job: input binding → Tool invocation → output capture → result publishing.
- Mutating ProcessSteps execute asynchronously via job queues; Workers pull jobs and execute Tools against Services.
- Non-mutating operations (e.g., read-only queries supporting UI) may bypass async queues for low-latency responses.
- Detailed execution lifecycle and worker orchestration patterns are specified in the Architecture documentation.

**Example**
```json
{
  "inputs": {
    "instruction": "Extract just the birthday",
    "content": "{step.searchResults}"
  },
  "output": {
    "variable": "birthday",
    "required": true
  }
}
```
Edges: `CALLS_TOOL -> tool-summarize`.

**Recursive Process Invocation Example**
```json
{
  "id": "step-compress-context",
  "inputs": {
    "sourceEpisodeIds": "{step.searchResults}",
    "targetCompressionRatio": "0.3"
  },
  "output": {
    "variable": "compressedSummary",
    "required": true
  }
}
```
Edges: `CALLS_PROCESS -> process-sequential-compression`.
This step invokes another Process recursively, enabling composition of complex workflows from simpler Processes.

---

### Conversation
**Purpose**
- Represents a user-owned dialogue tree whose turns are orchestrated by a Process.

**State**
- `id` (string, immutable)
- `title` (string, optional, mutable)
- `status` (`active` | `archived`)
- `createdAt`, `updatedAt`

**Process Selection Semantics**

**Conversation DEFAULT_PROCESS edge (UI hint)**
- Purpose: Persistent preference tracking for UI convenience.
- Mutability: Updates idempotently when user selects a Process for a new agent turn.
- Not execution source of truth: Reflects latest preference, not historical execution.
- Usage: UI shows “Next turn with [Process]” as default selector value.

**Alternative EXECUTED_BY edge (execution truth)**
- Purpose: Immutable audit trail of which Process created the alternative.
- Mutability: Set at alternative creation and never changes.
- Source of truth: Used for replay, debugging, analytics, and regenerations.
- Usage: Execution engine follows the Alternative’s `EXECUTED_BY` edge when running or re-running work.

**Update Flow Example**
```typescript
function createAgentTurn(conversationId, selectedProcessId) {
  const conversation = getConversation(conversationId);

  createOrUpdateDefaultProcessEdge(conversation.id, selectedProcessId);  // UI hint update

  const alternative = createAlternative({
    turnId: conversation.currentTurnId,
    content: ...,
    isActive: true
  });

  createExecutedByEdge(alternative.id, selectedProcessId);  // execution truth (immutable)
  executeProcess(selectedProcessId, ...);
}
```

**Key Insight:** DEFAULT_PROCESS edges may change as the user experiments; `EXECUTED_BY` edges preserve what actually ran so past responses remain traceable.

**Valid Mutations**
- **Create:** Instantiate root Conversation with assigned Process (`DEFAULT_PROCESS` edge) and owner (`OWNED_BY` edge).
- **Update:** Rename, switch Process hint via `DEFAULT_PROCESS` edge, archive/unarchive.
- **Delete:** **Not allowed.** Conversations are permanent audit records; archival is achieved via `status='archived'`, never by removal.

**Invariants**
- If `DEFAULT_PROCESS` edge exists it must target an enabled Process; null allowed for conversations that have never run an agent turn.

**Relationships**
- `Conversation --OWNED_BY--> User` (`created_at`)
- `Conversation --DEFAULT_PROCESS--> Process` (`since`)
- `Conversation --HAS_ACTIVE_ENTITY--> Entity` (`addedAt`, `relevance`)
- `Conversation --FORKED_FROM--> Conversation` (`originTurn`, `originAlternative`)
- `Conversation --HAS_TURN--> ConversationTurn` (`sequence`)

**Edge Constraints**
- `OWNED_BY` target: Immutable after creation. Ownership cannot transfer.
- `DEFAULT_PROCESS` target: Mutable. UI preference hint updated on each agent turn.
- `FORKED_FROM` target: Immutable if present. Fork provenance.
- `FORKED_FROM.originTurn`: Immutable. Fork point Turn.
- `FORKED_FROM.originAlternative`: Immutable. Fork point Alternative.
- `HAS_ACTIVE_ENTITY` edge set: Mutable. Updated as entities gain/lose relevance.

**References**
- `DEFAULT_PROCESS` edge records the current Process preference.
- Alternatives link to Processes via `EXECUTED_BY` edge.
- Conversation-to-Turn structure is expressed via `HAS_TURN` edge.
- Active entities recorded via `HAS_ACTIVE_ENTITY` edges.

**Notes**
- **Process selection scoped to alternatives:** Each agent alternative records the Process that produced it via `EXECUTED_BY` edge.
- **DEFAULT_PROCESS edge is UI convenience:** Updated idempotently to remember the user’s most recent Process choice for future turns.
- **Audit trail lives in alternatives:** To answer “which Process produced this response?” read the alternative (or its `EXECUTED_BY` edge), not the conversation.
- **Divergence expected:** DEFAULT_PROCESS edge may point to a different Process than older alternatives after the user changes preference; that’s intentional.

---

### ConversationTurn
**Purpose**
- Represents a structural position in the conversation tree where multiple alternative attempts may exist. Users can revise prompts; agents can respond with different Processes. Turns form a DAG where edges reference specific alternatives.

**State**
- `id` (string, immutable)
- `speaker` (`user` | `agent` | `system`)
- `turnType` (`message` | `tool_result` | `summary`)
- `content` (string, immutable after creation) - Permanent storage for display layer; NEVER deleted even after Episode sync completes
- `timestamp` (Date, immutable) - when Turn structure was created

**Alternative Structure:**
```json
{
  "id": "string",              // Alternative UUID
  "createdAt": "timestamp",
  "hasChildren": "boolean",    // Do other Turns reference this alternative?
  "cacheStatus": "valid | stale | generating"  // Does parent selection still match?
}
```

**Alternative Field Notes**
- Alternatives create `HAS_CONTENT` edges to Graphiti Episodes once ingestion completes. Alternatives are created synchronously while Graphiti ingestion is asynchronous. UI rendering uses Alternative content immediately; the edge powers semantic search, entity extraction, and knowledge-graph enrichment.

#### Episode Binding Lifecycle
1. **Turn + Alternative Created** – API stores immutable Turn structure and Alternative content (edge created without Episode target yet).
2. **Event Emitted** – `TurnCreated` (or equivalent) event notifies the Graphiti ingestion worker.
3. **Episode Written** – Worker generates the Graphiti Episode, naming it `Turn:{alternative.id}` (or using embedded Turn UUID) so it can be correlated later.
4. **Binding Backfill** – Worker polls Graphiti, matches on the naming convention, and establishes the `HAS_CONTENT` edge to the new Episode UUID. Entity extraction + semantic features now have a stable reference.

This async pattern keeps conversation UX responsive while still feeding the knowledge graph with authoritative content.

**Valid Mutations**
- **Create Turn:** Append new Turn with initial Alternative; connect via `HAS_TURN`, `HAS_ALTERNATIVE`, and `EXECUTED_BY`/`HAS_CONTENT` edges.
- **Add Alternative:** User edits create new user Alternative; different Process creates new agent Alternative. Each Alternative connects via `HAS_ALTERNATIVE` + `RESPONDS_TO` edges.
- **Switch Active:** Change which alternative has `HAS_ALTERNATIVE.isActive=true` (one per Turn).
- **Delete Turn/Alternative:** Not permitted; alternatives are preserved for audit.

**Invariants**
- Each Turn must belong to exactly one Conversation via `HAS_TURN` edge.
- Each Turn must have at least one Alternative with exactly one `HAS_ALTERNATIVE.isActive=true` (tracks what user is viewing).
- If `CHILD_OF` edge exists:
  - The referenced Turn must share the same Conversation.
  - Every Alternative’s `RESPONDS_TO` edge MUST target a valid Alternative in the parent Turn.
- Root Turns have no `CHILD_OF` edge; `RESPONDS_TO` edges are null/absent for their Alternatives.
- `HAS_TURN.sequence` values strictly increase along the main thread.
- User Turns can have multiple alternatives (revised prompts); Agent Turns can have multiple alternatives (Process variations); System Turns typically have a single alternative.

**Relationships**
- `Conversation --HAS_TURN--> ConversationTurn` (`sequence`)
- `ConversationTurn --CHILD_OF--> ConversationTurn` (`viaAlternative`)
- `ConversationTurn --HAS_ALTERNATIVE--> Alternative` (`isActive`, `sequence`)
- `Alternative --RESPONDS_TO--> Alternative` (preserves DAG provenance)
- `Alternative --HAS_CONTENT--> Episode` (`source`, `createdAt`)
- `Alternative --EXECUTED_BY--> Process` (`createdAt`)

**Edge Constraints**
- Incoming `HAS_TURN` from Conversation: Immutable. Turn cannot be moved between Conversations.
- `HAS_TURN.sequence`: Immutable. Depth-in-tree position.
- `CHILD_OF` target: Immutable after creation. Structural parent.
- `CHILD_OF.viaAlternative`: Immutable. Records which parent Alternative was active at creation.

**References**
- `HAS_CONTENT` edges link Alternatives to Graphiti Episodes.
- `RESPONDS_TO` edges identify which alternative in the parent Turn supplied the input.
- `EXECUTED_BY` edges record which Process produced each Alternative.

**Edge Constraints**
- `HAS_CONTENT` target: Initially null (async Episode creation). Once set, immutable. Backfilled by ingestion worker.
- `RESPONDS_TO` target: Immutable after creation. Locks which parent Alternative produced input.
- `EXECUTED_BY` target: Immutable after creation. Agent Alternatives only; user Alternatives have no `EXECUTED_BY` edge.
- `HAS_ALTERNATIVE.isActive`: Mutable. Only field that changes after Alternative creation.
- `HAS_ALTERNATIVE.sequence`: Immutable. Order within Turn.

**Notes**
- **User alternatives:** Created when user edits their prompt. Keeps bad attempts out of context.
- **Agent alternatives:** Created when user tries different Process, regenerates response, or continues from different parent alternative.
- **isActive semantics:** Tracked on `HAS_ALTERNATIVE.isActive`; system records selection, it doesn’t choose a canonical path.
- **Cache status derivation:** Agent alternative is "stale" when the `RESPONDS_TO` target no longer matches the parent Turn’s active `HAS_ALTERNATIVE` selection; user sees “this responded to a different upstream version.”
- **Context assembly:** WorkingMemory built by traversing `HAS_ALTERNATIVE.isActive=true` edges (user’s on-screen selections) from specified Turn back to root, ensuring clean context without correction chains or outdated responses.
- **User control:** System records what’s on screen and surfaces cache validity; user decides when to switch alternatives, regenerate responses, or continue the conversation.

---

### Episode
**Purpose**
- Holds the canonical content for each Turn, enabling semantic search and contextual retrieval. Episodes are managed by Graphiti.

**State** (Graphiti-defined)
- `uuid` (string, immutable) - Graphiti's identifier
- `name` (string, immutable) - typically matches turnId
- `content` (text, immutable) - the actual turn content
- `group_id` (string, immutable) - corresponds to conversationId
- `source` (string) - content type/origin
- `source_description` (string, optional)
- `entity_edges` (list of entity UUIDs extracted by Graphiti)
- `valid_at`, `created_at` (timestamps, immutable)

**Valid Mutations**
- Create: When Turn is recorded
- Update/Delete: Not permitted; Episodes are immutable

**Invariants**
- `group_id` must match the Conversation identifier
- `name` should reference a very brief summary description of the Turn content
- Tool results are kept concise before Episode creation

**Relationships** (Graphiti-managed)
- Entity extraction and semantic relationships handled by Graphiti
- Large content may be chunked with internal linking

**References**
- Alternatives link to Graphiti Episodes via `HAS_CONTENT` edges
- WorkingMemory references Episodes via Graphiti `uuid`

**Notes**
- Episodes automatically trigger entity extraction via Graphiti
- Extracted entities may be merged with user-created entities via deduplication
- **Multiple Episodes per Turn:** When a Turn has multiple alternatives, each alternative has its own `HAS_CONTENT` edge so Graphiti content reflects the specific user revision or agent Process response.

---

### WorkingMemory
**Purpose**
- Captures the curated subset of Turns, summaries, and entities currently “in mind” for a Conversation.

**State**
- `conversationId` (string)
- `currentTurnId` (string) - Turn from which context is assembled
- `currentAlternativeId` (string) - Alternative from which to trace back
- `immediatePath` (array of {turnId, alternativeId, episodeId}) - active path from current position back through ancestors
- `summaries` (list of summary IDs)
- `activeEntities` (array of EntityReference objects)
- `introspectionContext` (array of Introspection Episode UUIDs) - current carousel positions for agent persona (user-scoped, not conversation-scoped)
- `totalTokens` (number)
- `lastUpdated` (timestamp)

**Path Assembly**
- WorkingMemory context is built by traversing `isActive` alternatives from `currentTurnId:currentAlternativeId` back to the root. This ensures context reflects the specific path through the alternative tree while excluding stale alternatives.
- Computed view only: no persistent edges are stored. WorkingMemory derives its contents by traversing `HAS_ALTERNATIVE`, `HAS_SUMMARY`, `HAS_ACTIVE_ENTITY`, and `HAS_CONTENT` edges at read time.

**EntityReference Structure:**
```json
{
  "entityUuid": "string",        // Graphiti Entity UUID
  "name": "string",              // Cached for display
  "category": "string",          // Cached entity_type
  "relevanceScore": "number",    // 0-1, why it's in working memory
  "source": "user | graphiti | enrichment",
  "addedAt": "timestamp",
  "includeSummary": "boolean",
  "includeFacets": "boolean", 
  "includeRelationships": "boolean"
}
```

**Valid Mutations**
- **Create:** Instantiated when a Conversation begins.
- **Update:** After every Turn or alternative switch, `immediatePath`, summaries, entities, and token totals are recalculated.
- **Delete:** Occurs only when the Conversation is purged.

**Invariants**
- `totalTokens` must reflect sum of: immediatePath Episodes + summaries + activeEntities (with inclusion flags) + introspectionContext Episodes
- `immediatePath` contains only Episodes from `isActive=true` alternatives.
- Path traversal follows `CHILD_OF` edges for structure and each alternative’s `RESPONDS_TO` edge for specific parent responses; no skipped or inactive alternatives included.
- References point only to Turns/Summaries/Alternatives belonging to the same Conversation.

**Relationships**
- Scoped to a single Conversation (computed association; no persisted edge)

**References**
- References Episodes from `immediatePath` and summary layers plus Graphiti Entities by UUID (all derived from traversal results)

---

### Entity (Graphiti-Managed with Application Extensions)

**Purpose**
- Represents semantic concepts, people, objects, events, places, or organizations extracted from Episodes or explicitly created by users. Managed by Graphiti with application-specific extensions for enrichment and categorization.

**State** (Graphiti core schema)
- `uuid` (string, immutable) - Graphiti's identifier
- `name` (string, mutable) - Entity name
- `entity_type` (string, optional) - Category from faceted type system
- `summary` (string, mutable) - Short description
- `created_at` (timestamp, immutable)
- `valid_at` (timestamp, immutable)
- `group_id` (string) - typically conversationId for conversation-scoped entities
- `fact_ids` (array) - References to temporal facts about this entity
- `entity_edge_ids` (array) - Relationships to other entities

**State** (Application extensions)
- `sources` (array of EntitySource objects) - Tracks provenance
- `facets` (object, optional) - Type-specific metadata dimensions
- `enrichment` (object, optional) - AI-generated enhanced context
- `enriched_at` (timestamp, optional)
- `enriched_by` (processId, optional)

**EntitySource Structure:**
```json
{
  "type": "user | graphiti | enrichment",
  "created_at": "timestamp",
  "created_by": "userId (if type=user)",
  "episode_id": "episodeId (if type=graphiti)",
  "original_name": "string (before deduplication)",
  "confidence": "number (if AI-extracted)"
}
```

**Faceted Type System:**
```typescript
interface EntityTyping {
  category: 'Person' | 'Organization' | 'Project' | 'Concept' | 'Object' | 'Event' | 'Place';
  facets: {
    domain?: string[];        // ['technical', 'personal', 'professional']
    status?: string[];        // ['active', 'archived', 'planned']
    sentiment?: string[];     // ['positive', 'negative', 'neutral']
    // Category-specific facets discovered by enrichment
    [key: string]: string[];
  };
  confidence: {
    category: number;
    facets: Record<string, number>;
  };
  inferred_by: 'graphiti' | 'enrichment_process' | 'user';
}
```

**Valid Mutations**
- **Create:** User creates entity directly OR Graphiti extracts from Episode
- **Update:** Deduplication merges entities; enrichment adds facets/summary
- **Delete:** Graphiti entity lifecycle (application does not delete)

**Invariants**
- User-created entities must have name + basic summary
- Deduplication preserves all sources in merged entity
- Enrichment only adds to facets/enrichment fields, never removes sources
- Entity UUIDs are stable across deduplication (user-created UUID takes precedence)

**Relationships** (Graphiti-managed)
- `Entity --HAS_FACT--> TemporalFact`
- `Entity --RELATES_TO--> Entity` (via entity_edge_ids)
- `Episode --MENTIONS--> Entity` (via entity_edges in Episode)

**References**
- WorkingMemory.activeEntities array references by UUID
- Conversation.activeEntities array references by UUID

**User Creation Flow**
1. User creates entity with name, category (optional), description
2. System creates Graphiti Entity with source='user'
3. Entity immediately added to Conversation.activeEntities
4. Entity available in WorkingMemory for current turn
5. Subsequent Episodes may trigger Graphiti extraction
6. Deduplication merges user-created with AI-extracted entities
7. Background enrichment process enhances merged entities

**Deduplication**
- Graphiti's semantic similarity detects duplicate entities
- Merges based on name + summary similarity (threshold ~0.85)
- Preserves all sources (user + graphiti + enrichment)
- Chooses best name (user-provided takes precedence)
- Combines summaries and facts from both entities
- Updates all references to use merged UUID

**Enrichment Process**
- Triggered when entity's edge count crosses `enrichmentEdgeThreshold` (admin-configurable, default: 5)
- Edge count = number of Episodes or Summaries linking to this entity (tracked by Graphiti via entity_edges)
- Once triggered:
  - Semantic search finds all Episodes mentioning entity
  - Graph analysis explores entity neighborhood (relationships, centrality)
  - LLM synthesis creates enhanced summary and infers facets
  - Stores enrichment with confidence scores and provenance

---

### MetricDefinition
**Purpose**
- Defines a trackable metric that entities can report during execution.

**State**
- `id`, `name`, `description`
- `scope` (Service/Tool/Process/Conversation)
- `aggregation` (sum/avg/min/max/count/last)
- `dataType` (integer/float/boolean/timestamp)
- `retentionDays` (optional, for data lifecycle)
- `createdAt`, `updatedAt`

**Valid Mutations**
- Create/Update/Delete (admin only)

**Invariants**
- Metric names unique within scope
- Cannot delete metric with active values without cascade

---

### MetricValue
**Purpose**
- Records a specific metric measurement for an entity at a point in time.

**State**
- `metricId`
- `entityId` (Service/Tool/Process/Conversation ID)
- `value` (typed per MetricDefinition.dataType)
- `timestamp`
- `dimensions` (optional JSON for filtering: {userId, conversationId, etc})

**Valid Mutations**
- Create only (append-only for analytics)

**Invariants**
- MetricDefinition must exist
- Entity must exist
- Value type must match MetricDefinition.dataType

---

### Worker
**Purpose**
- Represents an execution unit that processes a single ProcessStep by invoking its referenced Tool against a Service. Workers consume jobs from queues and execute ProcessSteps asynchronously.

**State**
- `id` (string, immutable)
- `type` (string: type of work this worker handles, e.g., `graph_query`, `llm_call`, `rest_api`)
- `status` (`idle` | `busy` | `offline`; system-managed)
- `currentJobId` (string, nullable; references active job)
- `lastHeartbeat` (timestamp, system-managed)
- `processedCount` (integer; total jobs processed)
- `errorCount` (integer; total jobs failed)
- `createdAt`, `updatedAt`

**Valid Mutations**
- **Create:** System instantiates workers based on configured pool size per type
- **Update:** Status transitions managed by worker runtime; counts incremented on job completion
- **Delete:** Workers can be decommissioned when scaling down

**Invariants**
- Worker type must match the Service type of Tools it processes
- Workers with `status='offline'` cannot accept new jobs
- `currentJobId` must be null when `status='idle'`

**Relationships**
- `Worker --PROCESSES--> ProcessStep` (via job queue)
- `Worker --EXECUTES--> Tool` (during job execution)

**References**
- Jobs reference WorkerId during execution
- MetricValues may track per-Worker performance

**Notes**
- **Equivalence:** A Worker processes exactly one ProcessStep per job; "work unit" and "ProcessStep" are synonymous from execution perspective
- **Queue-based:** Workers pull jobs from queues (one queue per worker type); mutating operations are async, non-mutating UI queries bypass queues
- **Horizontal scaling:** Worker pool sizes configurable per type to match load
- **Job lifecycle:** Queued → Assigned to Worker → Executing → Completed/Failed

---

### Summary
**Purpose**
- Compressed representation of multiple Episodes, created by summarization Tools to manage context size.

**State**
- `id` (string, immutable)
- `compressionLevel` (integer: `max(sourceEpisode.compressionLevel) + 1`; immutable depth indicator)
- `tokenCount` (approximate size)
- `createdAt` (timestamp, immutable)

**Field Mutability**
- **Immutable:** `id`, `compressionLevel`, `createdAt`
- **Admin-mutable:** `tokenCount` (adjusted if new Episode length differs)

**Valid Mutations**
- **Create:** When compression Tool produces summary or admin manually backfills missing coverage, creating `SUMMARIZES`, `HAS_CONTENT`, `HAS_SUMMARY`, `COVERS_UP_TO`, and `CREATED_BY_PROCESS` edges.
- **Update (Admin only):** Rebind `HAS_CONTENT` to corrected Graphiti Episode; may adjust `tokenCount` to reflect revised content. Original Episode preserved for audit.
- **Delete (Admin only):** Removes Summary from conversation context; worker may schedule recompression to restore coverage.

**Invariants**
- Must reference at least one source Episode via `SUMMARIZES` edges.
- CompressionLevel must be one higher than max of source Episodes.
- `HAS_CONTENT` target must point to valid Graphiti Episode with source="summary".

**Relationships**
- `Conversation --HAS_SUMMARY--> Summary`
- `Summary --SUMMARIZES--> Episode` (`order`; one edge per source)
- `Summary --HAS_CONTENT--> Episode` (`source`, `createdAt`)
- `Summary --COVERS_UP_TO--> Turn`
- `Summary --CREATED_BY_PROCESS--> Process`
- WorkingMemory consumes Summary nodes for context (computed inclusion; no stored edge)

**Edge Constraints**
- `HAS_CONTENT` target: Immutable after creation. Admin repair creates NEW edge to corrected Episode; original edge preserved for audit.
- `SUMMARIZES` edge set: Immutable after creation. Source Episodes locked at compression time.
- `COVERS_UP_TO` target: Immutable. Marks compression boundary.
- `CREATED_BY_PROCESS` target: Immutable. Provenance record.
- Incoming `HAS_SUMMARY` from Conversation: Immutable. Summary cannot be moved between Conversations.

**References**
- WorkingMemory stores Summary IDs in `summaries` array (computed from `HAS_SUMMARY` edges)

---

### Introspection
**Purpose**
- Reflective note-to-self capturing evolving understanding, maintained in circular carousel as workspace for periodic reconsideration and creative reorganization.

**State**
- `id` (string, immutable)
- `carouselPosition` (integer, 0 to maxRotation-1)
- `conversationContext` (string, optional) - which conversation and compression event sequence triggered this (e.g., "conversation-123, compressions 45-49")
- `createdAt` (timestamp, immutable)

**Valid Mutations**
- **Create:** Generated by async introspection process or manual injection API
- **Update:** Rebinds the `HAS_CONTENT` edge to a new Graphiti Episode (persona corrections) while preserving provenance
- **Delete:** Removes entry from carousel and triggers rebalancing/archival; used to relocate or retire notes

**Invariants**
- Carousel has fixed size (maxRotation, e.g., 10)
- New introspection replaces oldest by position (position 0-9 cycle)
- Replaced notes archived but not deleted
- CarouselPosition must be within [0, maxRotation-1]; to move an entry to a new slot delete + recreate
- Must have valid `HAS_CONTENT` edge targeting Graphiti Episode with source='introspection'

**Relationships**
- `Introspection --HAS_CONTENT--> Episode` (`source`, `createdAt`)

**Edge Constraints**
- `HAS_CONTENT` target: Immutable after creation. Admin/user correction creates NEW edge; original preserved for audit.

**References**
- Stores Graphiti Episode UUID via `HAS_CONTENT` edge
- Episode `group_id` = 'system_introspection' (separate from conversation episodes)
- May reference conversationId in metadata for context

**Notes**
- Triggered asynchronously when cumulative WorkingMemory compressions reach `introspectionCompressionThreshold`
- `introspectionCompressionThreshold` is admin-configurable (default: 5 compressions, min: 1, max: 20)
- Counter tracks compressions since last introspection per conversation
- Reflective agent given:
  - **Warning:** Position X will be replaced - preserve vital information
  - All current carousel notes (full read access)
  - Recent compression events (last N summarizations)
  - Full tool access (semantic search, cypher queries)
  - Extended time budget for deep research and creative reorganization
  - **Freedom:** Use carousel positions however meaningful - may rewrite multiple, reorganize themes, distill patterns
  - **Goals:** Maintain developmental continuity, surface insights, track evolution
- Bootstrap: Empty carousel, agent creates initial notes
- Steady state: Agent reviews carousel before replacement, chooses how to preserve/reorganize
- User never waits - happens in background while conversation continues
- Content stored as Graphiti Episode enables:
  - Entity extraction from reflections (concepts, relationships discovered)
  - Semantic search across all introspections (current carousel + archived)
  - Temporal fact tracking (how understanding evolved)
  - Cross-referencing with conversation Episodes

---

## Key Patterns
- **Metadata hubs as nodes:** Service, Tool, Conversation, and Process hold rich metadata and expose explicit edges for observability and governance. Entities are managed by Graphiti with application extensions for enrichment.
- **Edge-primacy:** Structural relationships use edges (e.g., `OWNED_BY`, `HAS_TURN`, `HAS_ALTERNATIVE`, `CALLS_TOOL/CALLS_PROCESS`, `HAS_CONTENT`). Entity UUIDs still reference into Graphiti's graph.
- **Node-local alternatives:** ConversationTurns manage local alternative arrays (user edits, Process variations) while parent references specify which alternative was the input. WorkingMemory traverses only active alternatives, avoiding global branch semantics.
- **Meaningful edges only:** Edges represent true structural relationships (`USES`, `EXECUTES_ON`, `PARENT`, `FORK_FROM`, `CALLS`). ID properties handle soft references.
- **Recursive orchestration:** Processes may call other Processes (via Tools), and ConversationTurns form trees via `PARENT`/`FORK_FROM`, enabling deep recursion without redefining schemas.
- **Prompt templates in Tools, values from ProcessSteps:** LLM Tools define structured prompt templates; ProcessSteps inject runtime values via interpolation so prompts stay dynamic without hardcoding conversation state.

## Design Principles
- **Uniform storage:** Every concept—memory, orchestration, entities, credentials—flows through the same data fabric, with Graphiti managing entity semantics while application manages orchestration and context assembly.
- **Immutable history:** Turns and Episodes never mutate, preserving full audit trails and simplifying replay.
- **Separation of concerns:** Services define *where* work runs, Tools define *what* runs, and Processes define *how* work is sequenced.
- **Data-driven behavior:** All orchestration, validation, and health decisions originate from stored data (steps, schemas, statuses) rather than hardcoded logic.
- **Composability and recursion:** Workflows reference other workflows, and turns can fork or merge, letting the system evolve by configuration instead of refactors.
