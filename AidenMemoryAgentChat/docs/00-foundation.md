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
- `ownerId` (string, immutable; set from auth context)
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
- **Create:** Provide type, protocol, and connectionSchema defining parameter shape; capture `ownerId` from auth context; optionally originate from `serviceTemplateId`.
- **Update:** May adjust name, enabled flag, schema (with version increment); status updated via health checks.
- **Delete:** Allowed only when no Tools reference the Service.

**Invariants**
- Type and protocol combinations must match (e.g., `neo4j_graph` requires `bolt` or `bolt+s`).
- `connectionSchema` must be valid JSON Schema.
- Services with `requiresSecret=true` mandate that Tools provide `secretId` in their connection params.
- Disabled Services cannot report `status = healthy`.
- If Service uses `secretId`, Secret.ownerId MUST equal Service.ownerId (Secrets are never cross-user).
- Cross-owner references require sharing: Tool.ownerId != Service.ownerId → Service.shared MUST be true.

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
- `userId` (string, immutable; owner set from authenticated context)
- `name` (string, mutable)
- `type` (`api_key`, `oauth_token`, `password`, `certificate`; immutable)
- `encryptedValue` (opaque blob, immutable once written)
- `createdAt`, `updatedAt`
- `shared` (boolean, default `false`, mutable; Secrets remain owner-only even if set true)

**Valid Mutations**
- **Create:** Store encrypted payload and metadata; `userId` captured from auth context and never changed.
- **Update:** Rotate `encryptedValue`, rename, or change metadata without altering `id`.
- **Delete:** Allowed only when no Service currently `USES` it.

**Invariants**
- `encryptedValue` never leaves storage unredacted.
- `userId` is immutable ownership; all Secret reads/writes are filtered to the owning `userId`.
- Secret references (Service/Tool connection secretId, Process usage) MUST match the same `userId`; cross-user access returns 404.
- Secrets cannot be cross-user shared for execution; `shared` flag does not grant access beyond owner.
- Each Secret can be referenced by multiple Services but remains scoped per user.

**Relationships**
- `Service --USES--> Secret`
- `Secret --OWNED_BY--> User`

**References**
- Service records `connection.secretId` for credential lookup; Tool/Process execution validates the Secret belongs to the same user as the Conversation.

---

### Tool
**Purpose**
- Defines a single executable operation against a Service, providing concrete connection parameters that populate the Service's connectionSchema.

**State**
- `id` (string, immutable)
- `ownerId` (string, immutable; set from auth context)
- `name` (string, mutable)
- `serviceId` (string reference, immutable)
- `connectionParams` (object conforming to Service.connectionSchema)
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
- **Create:** Bind operation + schemas + connectionParams to existing Service; capture `ownerId` from auth; optionally originate from `toolTemplateId`.
- **Update:** Change description, schemas, operation parameters, or enabled flag.
- **Delete:** Allowed only when no ProcessSteps reference the Tool.

**Invariants**
- `connectionParams` must validate against Service `connectionSchema`.
- If Service has `requiresSecret=true`, connectionParams must include valid `secretId`.
- Cross-owner Service reference requires `Service.shared=true`; otherwise reject.
- Operation type must align with Service type.
- `inputSchema` keys must match variable names used inside `operation` definitions.

**Example**

Tool for specific Neo4j instance:
```json
{
  "serviceId": "service-neo4j-graphiti",
  "connectionParams": {
    "endpoint": "bolt://localhost:7687",
    "database": "graphiti",
    "secretId": "secret-neo4j-prod-creds",
    "maxConnectionPoolSize": 100
  },
  "operation": {
    "type": "graph_query",
    "query": "MATCH (n:Entity) WHERE n.name = $name RETURN n"
  }
}
```

Tool for specific LLM endpoint:
```json
{
  "serviceId": "service-anthropic-claude",
  "connectionParams": {
    "endpoint": "https://api.anthropic.com",
    "model": "claude-sonnet-4-20250514",
    "secretId": "secret-anthropic-api-key",
    "temperature": 0.7,
    "maxTokens": 4096
  },
  "operation": {
    "type": "llm_call",
    "systemPrompt": "You are a helpful assistant.",
    "promptTemplate": "{{instruction}}\n\n{{content}}"
  }
}

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
- ServiceTemplate, ToolTemplate, Service, Tool, and Secret all carry `ownerId` and `shared` flags with unified semantics: default private (`shared=false`), optionally discoverable when `shared=true`. Secrets remain owner-only even if marked shared; cross-user Secret execution is prohibited.
```

---

### Process
**Purpose**
- Orchestrates multiple Tools into a reusable workflow for context assembly, maintenance, or delegation.

**State**
- `id`, `name`, `description`
- `ownerId` (UUID, immutable; set from authenticated context)
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
- `Process --CALLS--> Tool`
- `Conversation --USES_PROCESS--> Process`

**References**
- Conversations store `processId`
- Tools may reference Processes for recursive execution (via `rest_call` operation type)

---

### ProcessStep
**Purpose**
- Represents one unit of work inside a Process, defined as part of the Process specification. Includes variable bindings, execution mode, and failure policy.

**State**
- `id` (string, unique per Process)
- `toolId` (string reference, optional) - References Tool for leaf operations
- `processId` (string reference, optional) - References Process for recursive orchestration
- `inputs` (map of parameter → interpolation expression)
- `output.variable` (string)
- `output.tokenBudget` (number, optional)
- `output.required` (boolean)
- `execution.mode` (`parallel` | `sequential`)
- `execution.condition` (string expression, optional)
- `execution.dependsOn` (list of step IDs)
- `execution.timeout` (number, optional)
- `execution.interactionMode` ('auto' | 'manual')

**Valid Mutations**
- Defined by mutating the parent Process; individual steps aren’t mutated independently.

**Invariants**
- `inputs` must match the requirements of the referenced Tool or Process.
- `dependsOn` cannot reference the step itself or form cycles; parallel steps cannot depend on each other.
- `dependsOn` cannot reference a step that is not mentioned prior to the dependant in the Process.
- `toolId` must refer to an enabled Tool whose Service is healthy when executed.
- `processId` must refer to an enabled Process within recursion limits.
- Exactly one of `toolId` or `processId` MUST be specified.
- If `processId` specified: inputs must satisfy target Process `initialContext` variables.
- If `toolId` specified: inputs must satisfy target Tool `inputSchema` specifications.
- Recursive Process invocation counts toward `maxRecursionDepth`.

**Relationships**
- Defined as part of the parent Process specification
- May reference a Tool (leaf operation) or another Process (recursive orchestration)

**References**
- Stores `toolId` (for Tool invocation) or `processId` (for Process recursion) plus `dependsOn` identifiers
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
  "toolId": "tool-summarize",
  "inputs": {
    "instruction": "Extract just the birthday",
    "content": "{step.searchResults}"
  }
}
```

**Recursive Process Invocation Example**
```json
{
  "id": "step-compress-context",
  "processId": "process-sequential-compression",
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
This step invokes another Process recursively, enabling composition of complex workflows from simpler Processes.

---

### Conversation
**Purpose**
- Represents a user-owned dialogue tree whose turns are orchestrated by a Process.

**State**
- `id` (string, immutable)
- `title` (string, optional, mutable)
- `userId` (string, immutable)
- `processId` (string reference, mutable) - **UI hint** tracking user’s most recently selected Process for new turns
- `status` (`active` | `archived`)
- `createdAt`, `updatedAt`
- `activeEntities` (array of Graphiti Entity UUIDs currently relevant to this conversation)
- `parentConversationId` (string, optional, immutable) - if this conversation was forked from another
- `forkOriginTurnId` (string, optional, immutable) - which turn in parent spawned this fork
- `forkOriginAlternativeId` (string, optional, immutable) - which alternative in the parent Turn was active when the fork occurred (complete provenance of “what the user saw” at fork time)

**Process Ownership Semantics**

**Conversation.processId (UI hint)**
- Purpose: Persistent preference tracking for UI convenience.
- Mutability: Updates idempotently when user selects a Process for a new agent turn.
- Not execution source of truth: Reflects latest preference, not historical execution.
- Usage: UI shows “Next turn with [processId]” as default Process selector value.

**Alternative.processId (execution truth)**
- Purpose: Immutable audit trail of which Process created the alternative.
- Mutability: Set at alternative creation and never changes.
- Source of truth: Used for replay, debugging, analytics, and regenerations.
- Usage: Execution engine reads Alternative.processId when running or re-running work.

**Update Flow Example**
```typescript
function createAgentTurn(conversationId, selectedProcessId) {
  const conversation = getConversation(conversationId);

  const alternative = {
    episodeId: null,
    processId: selectedProcessId,   // execution truth (immutable)
    isActive: true,
    cacheStatus: 'generating',
    inputContext: { parentAlternativeId: ... }
  };

  conversation.processId = selectedProcessId;  // UI hint update

  executeProcess(alternative.processId, ...);  // Always use alternative’s processId
}
```

**Key Insight:** Conversation.processId may change as user experiments with Claude/GPT-4/etc. Alternative.processId preserves what actually ran so past responses remain traceable.

**Valid Mutations**
- **Create:** Instantiate root conversation with assigned Process.
- **Update:** Rename, switch Process hint, archive/unarchive.
- **Delete:** **Not allowed.** Conversations are permanent audit records; archival is achieved via `status='archived'`, never by removal.

**Invariants**
- If `processId` is set it must reference an enabled Process; null allowed for conversations that have never run an agent turn.

**Relationships**
- `Conversation --HAS_TURN--> ConversationTurn`
- `WorkingMemory --BELONGS_TO--> Conversation`

**References**
- Conversation.processId references a Process as mutable UI hint.
- ConversationTurn alternatives reference Processes via `alternative.processId` as immutable execution truth.
- Turns and WorkingMemory store `conversationId` as properties.
- activeEntities array stores Graphiti Entity UUIDs (references into Graphiti graph).

**Notes**
- **Process selection scoped to alternatives:** Each agent alternative records the Process that produced it via `alternative.processId`.
- **Conversation.processId is UI convenience:** Updated idempotently to remember the user’s most recent Process choice for future turns.
- **Audit trail lives in alternatives:** To answer “which Process produced this response?” read the alternative, not the conversation.
- **Divergence expected:** Conversation.processId may differ from older alternatives after the user changes preference; that’s intentional.

---

### ConversationTurn
**Purpose**
- Represents a structural position in the conversation tree where multiple alternative attempts may exist. Users can revise prompts; agents can respond with different Processes. Turns form a DAG where edges reference specific alternatives.

**State**
- `id` (string, immutable)
- `conversationId` (string, immutable)
- `parentTurnId` (string reference, nullable) - structural parent in conversation tree
- `sequence` (number)
- `speaker` (`user` | `agent` | `system`)
- `turnType` (`message` | `tool_result` | `summary`)
- `content` (string, immutable after creation) - Permanent storage for display layer; NEVER deleted even after Episode sync completes
- `alternatives` (array of Alternative objects, mutable) - multiple attempts at this conversation position
- `timestamp` (Date, immutable) - when Turn structure was created

**Alternative Structure:**
```json
{
  "id": "string",              // Alternative UUID
  "episodeId": "string | null",       // Graphiti Episode UUID (async binding; null until worker backfills)
  "processId": "string",       // Process that generated this (agent turns only)
  "createdAt": "timestamp",
  "isActive": "boolean",       // True if this alternative is currently displayed in UI

  // Input context: complete provenance for path reconstruction
  "inputContext": {
    "parentAlternativeId": "string"    // Which alternative in that Turn was active (null for root Turn alternatives)
  },
  
  // Derived/computed state (not persisted)
  "hasChildren": "boolean",    // Do other Turns reference this alternative?
  "cacheStatus": "valid | stale | generating"  // Does parent selection still match?
}
```

**Alternative Field Notes**
- `episodeId` (UUID, nullable): Graphiti Episode containing the alternative’s content. This begins as `null` because Alternatives are created synchronously with the Turn while Graphiti ingestion is asynchronous. The ingestion worker later backfills this field once it correlates the new Episode (named `Turn:{alternative.id}`) to the Alternative. UI rendering always uses `Alternative.content`, so users see responses immediately even before `episodeId` is populated. Episode binding primarily powers semantic search, entity extraction, and knowledge-graph enrichment.

#### Episode Binding Lifecycle
1. **Turn + Alternative Created** – API stores immutable Turn structure and Alternative content with `episodeId = null`.
2. **Event Emitted** – `TurnCreated` (or equivalent) event notifies the Graphiti ingestion worker.
3. **Episode Written** – Worker generates the Graphiti Episode, naming it `Turn:{alternative.id}` (or using embedded Turn UUID) so it can be correlated later.
4. **Binding Backfill** – Worker polls Graphiti, matches on the naming convention, and updates `Alternative.episodeId` to the new Episode UUID. Entity extraction + semantic features now have a stable reference.

This async pattern keeps conversation UX responsive while still feeding the knowledge graph with authoritative content.

**Valid Mutations**
- **Create Turn:** Append new Turn with initial alternative referencing Episode + Process.
- **Add Alternative:** User edits create new user alternative; different Process creates new agent alternative.
- **Switch Active:** Change which alternative has `isActive=true` (one per Turn).
- **Delete Turn/Alternative:** Not permitted; alternatives are preserved for audit.

**Invariants**
- Each Turn must belong to exactly one Conversation.
- Each Turn must have at least one alternative with exactly one `isActive=true` (tracks what user is viewing).
- If `parentTurnId` is set:
  - The referenced Turn must share the same Conversation.
  - Every alternative’s `inputContext.parentAlternativeId` MUST reference a valid alternative in the parent Turn.
- If `parentTurnId` is null (root Turn):
  - All alternatives must have `inputContext.parentAlternativeId = null`.
- `sequence` values strictly increase along the main thread.
- User Turns can have multiple alternatives (revised prompts); Agent Turns can have multiple alternatives (Process variations); System Turns typically have a single alternative.

**Relationships**
- `Conversation --HAS_TURN--> ConversationTurn`
- `ConversationTurn --NEXT--> ConversationTurn` (via parentTurnId; each alternative records which parent alternative it responded to via `inputContext.parentAlternativeId`)
- `ConversationTurn.alternatives[].episodeId` references Episode in Graphiti
- `ConversationTurn --FORK_ORIGIN--> ConversationTurn` (first turn in forked conversation references the turn in parent that spawned it)

**References**
- Stores `episodeId` per alternative linking to Graphiti content.
- Alternatives store `inputContext.parentAlternativeId` identifying which alternative in the parent Turn (located via `parentTurnId`) supplied the input for this alternative.

**Notes**
- **User alternatives:** Created when user edits their prompt. Keeps bad attempts out of context.
- **Agent alternatives:** Created when user tries different Process, regenerates response, or continues from different parent alternative.
- **isActive semantics:** Tracks which alternative the user currently has displayed in the UI; system records selection, it doesn’t choose a canonical path.
- **Cache status derivation:** Agent alternative is "stale" when `inputContext.parentAlternativeId` no longer matches the parent Turn’s active alternative; user sees “this responded to a different upstream version.”
- **Context assembly:** WorkingMemory built by traversing `isActive` alternatives (user’s on-screen selections) from specified Turn back to root, ensuring clean context without correction chains or outdated responses.
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
- ConversationTurns store Graphiti's `uuid` as `episodeId`
- WorkingMemory references Episodes via Graphiti `uuid`

**Notes**
- Episodes automatically trigger entity extraction via Graphiti
- Extracted entities may be merged with user-created entities via deduplication
- **Multiple Episodes per Turn:** When a Turn has multiple alternatives, each alternative owns a distinct `episodeId` so Graphiti content reflects the specific user revision or agent Process response.

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
- Path traversal follows Turn.parentTurnId for structure and each alternative’s `inputContext.parentAlternativeId` for specific parent responses; no skipped or inactive alternatives included.
- References point only to Turns/Summaries/Alternatives belonging to the same Conversation.

**Relationships**
- `WorkingMemory --BELONGS_TO--> Conversation`

**References**
- References Episodes from `immediatePath` and summary layers plus Graphiti Entities by UUID

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
- `conversationId` (string, immutable)
- `episodeId` (string, points to summary content in Graphiti)
- `sourceEpisodeIds` (array of Episode UUIDs that were compressed; immutable provenance)
- `compressionLevel` (integer: `max(sourceEpisode.compressionLevel) + 1`; immutable depth indicator)
- `priorTurnId` (string, captures last Turn included in compression window)
- `tokenCount` (approximate size)
- `createdBy` (processId that created this summary)
- `createdAt` (timestamp, immutable)

**Field Mutability**
- **Immutable:** `id`, `conversationId`, `sourceEpisodeIds`, `compressionLevel`, `priorTurnId`, `createdAt`, `createdBy`
- **Admin-mutable:** `episodeId` (may be repointed to corrected Episode content), `tokenCount` (adjusted if new Episode length differs)

**Valid Mutations**
- **Create:** When compression Tool produces summary or admin manually backfills missing coverage
- **Update (Admin only):** Repoint `episodeId` to corrected Graphiti Episode; may adjust `tokenCount` to reflect revised content. Original Episode preserved for audit.
- **Delete (Admin only):** Removes Summary from conversation context; worker may schedule recompression to restore coverage.

**Invariants**
- Must reference at least one source Episode
- CompressionLevel must be one higher than max of source Episodes
- EpisodeId must point to valid Graphiti Episode with source="summary"

**Relationships**
- `Summary --SUMMARIZES--> Episode` (many source Episodes)
- `Summary --HAS_CONTENT--> Episode` (one Graphiti Episode for content)
- `WorkingMemory --REFERENCES--> Summary`

**References**
- WorkingMemory stores Summary IDs in `summaries` array

---

### Introspection
**Purpose**
- Reflective note-to-self capturing evolving understanding, maintained in circular carousel as workspace for periodic reconsideration and creative reorganization.

**State**
- `id` (string, immutable)
- `episodeId` (string, Graphiti UUID reference, immutable) - points to Episode containing reflection content
- `carouselPosition` (integer, 0 to maxRotation-1)
- `conversationContext` (string, optional) - which conversation and compression event sequence triggered this (e.g., "conversation-123, compressions 45-49")
- `createdAt` (timestamp, immutable)

**Valid Mutations**
- **Create:** Generated by async introspection process or manual injection API
- **Update:** Replaces `episodeId` pointer to a new Graphiti Episode (persona corrections) while preserving provenance
- **Delete:** Removes entry from carousel and triggers rebalancing/archival; used to relocate or retire notes

**Invariants**
- Carousel has fixed size (maxRotation, e.g., 10)
- New introspection replaces oldest by position (position 0-9 cycle)
- Replaced notes archived but not deleted
- CarouselPosition must be within [0, maxRotation-1]; to move an entry to a new slot delete + recreate
- Must have valid episodeId referencing Graphiti Episode with source='introspection'

**Relationships**
- `Introspection --HAS_CONTENT--> Episode` (via episodeId reference)

**References**
- Stores Graphiti Episode UUID as `episodeId`
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
- **References via identifiers:** Frequently-used relationships (episodeId, toolId, serviceId, conversationId, entityUuid) rely on identifier references rather than explicit edges for efficiency. Entity UUIDs reference into Graphiti's graph.
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
