# Phase 5 Business Rules

## Introduction
This document defines the invariants, constraints, and business logic that govern the Aiden Memory Agent Chat system. These rules are implementation-agnostic and represent the **core domain knowledge** - they must hold true regardless of technology choices, database implementations, or UI frameworks.

Business rules are organized by domain concept and numbered for traceability. Each rule includes:
- **Rule ID:** Unique identifier (format: `BR-<CONCEPT>-<NUMBER>`)
- **Category:** Type of rule (Invariant, Constraint, Validation, Process, Calculation)
- **Description:** What the rule enforces
- **Rationale:** Why this rule exists
- **Violation Impact:** What breaks if rule is violated

---

## Service Rules

### BR-SERVICE-001: Type-Protocol Compatibility
**Enforcement:** API

**Category:** Invariant  
**Description:** Service type must align with its connection protocol:
- `neo4j_graph` → `bolt` or `bolt+s` protocols only
- `rest_api` → `http` or `https` protocols only
- `llm_provider` → `http` or `https` protocols only
- `mcp_server` → `stdio` or `sse` protocols only

**Rationale:** Protocol mismatches cause runtime connection failures that are difficult to debug.

**Violation Impact:** Service creation/update fails; existing connections become unusable.

---

### BR-SERVICE-002: Secret Requirements
**Enforcement:** API

**Category:** Invariant  
**Description:** Services with `requiresSecret=true` establish that ALL Tools using this Service MUST provide valid `secretId` in their `connectionParams`.

**Rationale:** Service-level secret requirement enforces security policy at the template level.

**Violation Impact:** Tools attempting to connect without credentials; security vulnerability.

---

### BR-SERVICE-003: Health Status Management
**Enforcement:** Worker

**Category:** Process  
**Description:** Service `status` is system-managed through health checks:
- `enabled=false` → status CANNOT be `healthy`
- Health checks update status atomically
- Status transitions: `healthy` ↔ `degraded` ↔ `down`
- Manual status overrides are prohibited

**Rationale:** Ensures status reflects actual system state, not assumptions.

**Violation Impact:** System may attempt operations against unavailable services; misleading observability.

---

### BR-SERVICE-004: Deletion Safety
**Enforcement:** API

**Category:** Constraint  
**Description:** A Service CANNOT be deleted if:
- Any Tool has `serviceId` referencing it
- Service is referenced in active Process execution context

**Rationale:** Prevents orphaning Tools and breaking active workflows.

**Violation Impact:** Tools become unexecutable; Processes fail mid-execution.

---

### BR-SERVICE-005: Connection Schema Validity
**Enforcement:** API

**Category:** Validation  
**Description:** Service `connectionSchema` MUST be valid JSON Schema (draft-07 or later) defining connection parameter requirements.

**Rationale:** Ensures Tools can be validated against well-defined parameter shape.

**Violation Impact:** Ambiguous Tool configuration; runtime connection failures.

---

### BR-SERVICE-006: Schema-Protocol Consistency
**Enforcement:** API

**Category:** Invariant  
**Description:** Service `connectionSchema` must include parameters appropriate for `protocol`:
- `bolt`/`bolt+s` → requires `endpoint` (bolt:// or bolt+s:// URI)
- `http/https` → requires `endpoint` (http(s):// URI)
- `stdio` → requires `command` and optional `args` array
- `sse` → requires `endpoint` (http(s):// URI with SSE support)

**Rationale:** Protocol-specific parameters enable correct connection establishment.

**Violation Impact:** Tools cannot connect; runtime protocol errors.

---

## Sharing & Template Rules

### BR-SHARE-001: Default Sharing (Immutable Initial State)
**Enforcement:** Domain

**Category:** Invariant  
**Description:** ServiceTemplate, ToolTemplate, Service, Tool, and Secret default to `shared=false`. Only the owner (`ownerId`) can view/use/modify a private entity. Initial creation sets visibility; future toggles must respect dependency checks.

**Rationale:** Privacy by default; no accidental exposure.

**Violation Impact:** Private resources leak to other users.

---

### BR-SHARE-002: Shared Visibility
**Enforcement:** API

**Category:** Invariant  
**Description:** When `shared=true`, an entity becomes discoverable and referenceable by all authenticated users. Non-owners may view metadata and reference the entity but cannot modify or delete it. Responses include owner attribution.

**Rationale:** Enables safe reuse while preserving ownership boundaries.

**Violation Impact:** Users cannot find or reuse shared resources; or unauthorized edits occur.

---

### BR-SHARE-003: Visibility Rule (Composite)
**Enforcement:** Domain

**Category:** Invariant  
**Description:** User U can view entity E if `(E.ownerId == U.userId) OR (E.shared == true)`. User U can modify/delete E only if `E.ownerId == U.userId`.

**Rationale:** Clear, consistent access semantics across all five entity types.

**Violation Impact:** Unauthorized visibility or edits.

---

### BR-SHARE-004: Deletion Safety Across Ownership
**Enforcement:** API

**Category:** Constraint  
**Description:** An entity CANNOT be deleted (or unshared) if other users’ entities reference it. Example: Cannot delete `Service(shared=true)` if User B’s Tool references it. Return `409 Conflict` with dependency reason.

**Rationale:** Prevents breaking other users’ resources.

**Template Exemptions:**
ServiceTemplate and ToolTemplate archival/deletion is NOT blocked by instance references:
- `serviceTemplateId` and `toolTemplateId` are audit-only provenance fields
- Instances contain complete copied structure (operational independence)
- Template archival allowed regardless of how many Services/Tools reference it
- Instance operation unaffected by template archival (no broken functionality)

**Examples requiring 409 blocking:**
- Service deletion: blocked if Tools reference it (operational dependency)
- Secret deletion: blocked if Services reference it (operational dependency)  
- Process deletion: blocked if Conversations reference it (operational dependency)

**Examples NOT requiring blocking:**
- ServiceTemplate archival: allowed even if 100 Services have serviceTemplateId pointing to it
- ToolTemplate archival: allowed even if 50 Tools have toolTemplateId pointing to it

**Violation Impact:** Downstream operational failures for other users; broken references cause execution errors. 

**Note:** Template references are exempt—they are provenance-only and do not cause operational failures when template is archived.

---

### BR-SHARE-005: Cross-User Reference Rules
**Enforcement:** API

**Category:** Validation  
**Description:** Cross-owner references require sharing:
- If `Tool.ownerId != Service.ownerId`, then `Service.shared` MUST be true.
- If `Service.ownerId != Tool.ownerId` referencing it, then `Tool.shared` MUST be true when referenced back across ownership.
- Violations return 422 Business Rule Violation.

**Rationale:** Ensures mutual consent for cross-user reuse.

**Violation Impact:** Private resources referenced without permission; unexpected exposure.

---

### BR-SHARE-006: Service-Secret Ownership (Immutable)
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Secrets remain owner-scoped and cannot be used cross-user. If Service.ownerId != Secret.ownerId, creation/update fails; execution must halt with 403/422 semantics. Secret.shared does not grant cross-user access.

**Rationale:** Credentials must never cross tenant boundaries.

**Violation Impact:** Credential leakage; execution failures.

---

### BR-SHARE-007: Execution Chain Validation
**Enforcement:** Worker

**Category:** Validation  
**Description:** On execution of Tool within Conversation:
- If `Conversation.userId != Tool.ownerId`, require `Tool.shared=true` or reject (404/403 per API policy).
- If `Tool.ownerId != Service.ownerId`, require `Service.shared=true` or reject (422).
- Service → Secret must satisfy `Secret.ownerId == Service.ownerId`; otherwise reject (403/422).
- Audit captures executor.userId and resource owners.

**Rationale:** Enforces ownership alignment at runtime.

**Violation Impact:** Private resources executed by other users; secret misuse.

---

### BR-SHARE-008: Shared Resource Cost Attribution
**Enforcement:** Worker

**Category:** Invariant  
**Description:** When user U executes a shared resource owned by user O, resource consumption (tokens, credentials) is attributed to owner O. No reimbursement/refund logic.

**Rationale:** Cost attribution follows ownership of underlying credentials.

**Violation Impact:** Mis-billed resource usage; audit gaps.

---

### BR-SHARE-009: Unsharing Effects (Warn-and-Allow Model)
**Enforcement:** API

**Category:** Resource Management  
**Priority:** High  
**Description:** When resource owner sets shared=false (revokes sharing):

**Pre-action warning (advisory only, does NOT block):**
- System queries for dependent resources owned by other users
- If found: Returns 200 OK with warning metadata in response
- Owner sees impact summary but action proceeds immediately

**Immediate effects:**
- shared flag set to false in database
- Resource immediately hidden from other users' listings
- No grace period, no deferred execution

**Runtime effects on dependent resources:**
- Dependent Processes remain in database with executable=true
- Process executions fail at runtime with 422:
  "Process step [N] references inaccessible Tool [name] owned by [user]"
- Failure logs capture:
  * Tool ID and name
  * Owner who revoked sharing
  * Timestamp of failure
  * ProcessStep that failed

**User Experience:**
- **Owner:** Sees "⚠️ Warning: N Processes owned by M users depend on this resource"; action still completes.
- **Dependent user:** Execution fails with diagnostic: "⚠️ Process broken - Tool [name] no longer shared by owner"; suggested action: contact owner or replace Tool.

**Design Principle:**
Owner controls resources and spending. System warns, documents, and fails gracefully. External failures (revoked secrets, expired credentials, unavailable APIs) are indistinguishable from internal breaks (unsharing). Both handled by runtime validation (BR-EXEC-003).

**Validation:** None at unshare time. Runtime validation (BR-EXEC-003) handles failures.

**Violation Impact:** None when unsharing. Dependent Processes fail at execution with clear diagnostics.

---

### BR-SHARE-010: Cross-User Audit Trail
**Enforcement:** Worker

**Category:** Invariant  
**Description:** All cross-user resource usage is logged with executor.userId, resource.ownerId, resource.id, and timestamp for attribution and review.

**Rationale:** Enables accountability and cost tracking.

**Violation Impact:** Cannot trace cross-tenant usage.

---

### BR-TEMPLATE-001: Template Immutability
**Enforcement:** Domain

**Category:** Invariant  
**Template Creation:**
Any authenticated user may create ServiceTemplates and ToolTemplates. No special permissions or admin privileges required beyond valid authentication token.

**Template Reference Semantics:**
- `serviceTemplateId` and `toolTemplateId` are immutable audit fields for provenance tracking
- These references are NOT operational dependencies
- Template archival is never blocked by instance references
- Instances contain complete copied structure and operate independently
- Soft references may point to archived templates (graceful degradation in UI)

**Description:** ServiceTemplate and ToolTemplate structural fields (type/protocol/connectionSchema/operation/inputSchema/outputSchema) are immutable after creation. Only name, description, and `shared` may change.

**Rationale:** Templates provide stable blueprints.

**Violation Impact:** Previously instantiated Services/Tools drift from blueprint; reproducibility fails.

---

### BR-TEMPLATE-002: Template Instantiation
**Enforcement:** API

**Category:** Process  
**Description:** Instantiating a Service/Tool from a template performs complete structural copy:
- Service/Tool receives full copy of all structural fields (type/protocol/schema for Service; operation/schemas for Tool)
- Instance stores immutable templateId as audit trail (provenance only, not operational dependency)
- Instance gets own ownerId, shared flag, and all mutable state fields
- Template archival does NOT block on instance references (instances have complete copies)
- Template archival does NOT affect existing instances (they operate independently)
- Template changes NEVER propagate to instances (no retroactive updates)
- Instance.templateId may point to archived template (soft reference, graceful UI degradation)

**Rationale:** Ensures predictability of instantiated resources.

**Violation Impact:** Instances change unexpectedly; audit trails break.

---

### BR-TEMPLATE-003: Template Immutability
**Enforcement:** Domain
**Category:** Data Integrity  
**Priority:** High  
**Applies To:** ServiceTemplate, ToolTemplate

**Rule:**
Templates are immutable after creation except for:
- `archived` flag (toggle via archive/unarchive operations)
- `shared` flag (toggle via PUT /templates/{id}/share)

Immutable fields:
- Structural: `type`, `protocol`, `connectionSchema` (ServiceTemplate)
- Structural: `operation`, `inputSchema`, `outputSchema` (ToolTemplate)
- Metadata: `name`, `description`
- Identity: `ownerId`

**Rationale:**
Templates are blueprints. Instances receive full structural copy (denormalized model), so template changes don't affect existing instances. Allowing modification creates confusion about "which version" without providing value.

**Versioning Strategy:**
- Create new template with desired changes
- Optionally version in name ("FooService v2")
- Archive old template when superseded
- No built-in versioning system

**Validation:**
- PUT endpoints reject attempts to modify immutable fields with 422
- Only `archived` and `shared` flags are mutable

**Violation Impact:**
Request rejected with 422 Unprocessable Entity listing immutable fields attempted.

---

### BR-TEMPLATE-004: Template Sharing & Cost
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Shared templates are discoverable at zero execution cost; users must instantiate with their own Services/Secrets. Costs accrue only when using instantiated resources.

**Rationale:** Encourages sharing blueprints without subsidizing execution.

**Violation Impact:** Misaligned cost expectations; template use blocked.

---

### BR-TEMPLATE-006: Template Archival (Soft Delete)
**Enforcement:** API
**Category:** Data Management  
**Priority:** Medium  
**Applies To:** ServiceTemplate, ToolTemplate

**Rule:**
Templates use soft delete (archived flag). Effects:

**Active templates (archived=false):**
- Visible in default listings
- Available for instantiation
- Shown in UI template pickers

**Archived templates (archived=true):**
- Hidden from default listings (unless ?includeArchived=true)
- Still retrievable via GET /templates/{id}
- NOT available for new instantiation (422 if user attempts)
- Existing instances unaffected
- templateId references remain valid

**Archival is reversible:** Set archived=false to restore.

**Rationale:**
Preserves audit trail, maintains referential integrity, allows undelete if needed. Soft delete ensures instance templateId fields never become dangling references.

**Validation:**
- POST /templates with archived template: 422 "Cannot instantiate from archived template"
- GET /templates by default excludes archived (unless ?includeArchived=true)
- GET /templates/{id} works regardless of archived status

**Violation Impact:**
None - archival is advisory. Existing instances continue functioning identically whether template is active or archived.

---

### BR-TEMPLATE-007: Instance Discovery
**Enforcement:** API
**Category:** Observability  
**Priority:** Low  
**Applies To:** ServiceTemplate, ToolTemplate

**Rule:**
Template instance discovery via GET /templates/{id}/instances.

**Returns instances where:**
- Instance.templateId = template.id (soft reference match)
- Instance owned by requester OR instance.shared = true

**Notes:**
- Count may be stale (instances deleted after instantiation)
- Soft reference may point to archived template (still valid)
- Performance: O(n) scan optimized with index on templateId
- Pagination required for templates with many instances

**Use Case:**
Before archiving template, check impact on ecosystem. Advisory information for owner to understand template usage.

**Validation:**
None - read-only query.

**Violation Impact:**
N/A

---

## Secret Rules

### BR-SECRET-001: Immutable Encryption & User Ownership (UPDATED)
**Enforcement:** Domain

**Category:** Invariant  
**Description:** 
- Once `encryptedValue` is written, it can only be replaced via rotation (creating new `encryptedValue` with new `updatedAt`), never decrypted or exposed in logs/responses.
- `userId` is immutable and establishes ownership within multi-tenant system.
- Secret belongs exclusively to its owner; cross-user access prohibited.

**Rationale:** Secrets are write-only from application perspective; user ownership prevents cross-tenant credential leakage; protects against credential exposure.

**Violation Impact:** Security vulnerability; credential exposure; multi-tenant isolation breach.

---

### BR-SECRET-002: Deletion Safety
**Enforcement:** API

**Category:** Constraint  
**Description:** A Secret CANNOT be deleted if any Tool currently has secretId in connectionParams referencing it.

**Rationale:** Prevents breaking active service connections.

**Violation Impact:** Services lose authentication; all dependent operations fail.

---

### BR-SECRET-002A: User-Scoped Ownership (NEW)
**Enforcement:** API

**Category:** Invariant  
**Description:** Every Secret MUST have explicit `userId` owner set at creation:
- Secret created by user → `userId` set to that user
- `userId` immutable after creation
- All Tools referencing this Secret must belong to Conversation(s) owned by same userId
- Cross-user Secret access is prohibited (API returns 404 to non-owner)

**Rationale:** Multi-tenant isolation; prevents users accessing each other's credentials.

**Violation Impact:** Security vulnerability; credential leakage between users.

---

### BR-SECRET-002B: User-Tool-Secret Alignment (NEW)
**Enforcement:** API

**Category:** Validation  
**Description:** When ProcessStep references a Tool with `secretId` in connectionParams:
- Tool's referenced Service must exist and belong to user's workspace
- Secret must have `userId` matching Tool's owning user
- At execution time, verify Conversation belongs to same userId
- Cross-user credentials rejected with 403 Forbidden

**Shared Tool + Secret Implications:**
When Tool is shared (shared=true) and requires Secret (requiresSecret=true):
- Secret.userId = Tool.ownerId (tool owner's Secret)
- Tool owner pays token costs when shared Tool is executed by others
- Shared infrastructure costs remain with Secret owner
- Share carefully - sharing Tool with Secret delegates payment responsibility

**Rationale:** Ensures credential access aligns with ownership boundaries.

**Violation Impact:** User accidentally uses another user's credentials; data leakage or service misconfiguration.

---

### BR-SECRET-003: Type-Appropriate Usage
**Enforcement:** API

**Category:** Validation  
**Description:** Secret type must match Service usage:
- `api_key` → used in headers or query parameters
- `oauth_token` → used with refresh flow
- `password` → used in basic auth
- `certificate` → used for mTLS

**Rationale:** Enforces proper credential handling patterns.

**Violation Impact:** Authentication failures; security best practices violated.

---

## Cross-User Validation Sequences

**Scenario A: Tool references another user's Service**
1. Verify Service exists; else 404.
2. Authorize visibility: owner OR `Service.shared=true`; else 404.
3. Set Tool.ownerId = authenticated user.
4. If Tool.ownerId != Service.ownerId, require `Service.shared=true`; else 422 (BR-SHARE-005).
5. Create Tool.

**Scenario B: Execution with private Tool**
1. Conversation.userId = executor.
2. Tool.ownerId may differ.
3. If executor != Tool.ownerId and `Tool.shared=false`, reject (403 or 404 per access policy) referencing BR-SHARE-007.

**Scenario C: Service uses foreign Secret**
1. Service.ownerId = authenticated user.
2. Secret.ownerId must equal Service.ownerId; else reject 422 (BR-SHARE-006) before persistence.

**Scenario D: Execution ownership chain**
1. Conversation.userId → Tool.ownerId: require `Tool.shared=true` if different.
2. Tool.ownerId → Service.ownerId: require `Service.shared=true` if different.
3. Service.ownerId → Secret.ownerId: must match exactly; otherwise reject (403/422).
4. Audit executor and resource owners (BR-SHARE-007, BR-SHARE-009).

---

## Tool Rules

### BR-TOOL-001: Connection Params Schema Conformance
**Enforcement:** API

**Category:** Validation  
**Description:** Tool `connectionParams` MUST conform to the `connectionSchema` defined by referenced Service, including:
- All required properties present
- Property types match schema
- Values within defined constraints (min/max, format, enum)
- If Service `requiresSecret=true`, `secretId` must be provided and valid

**Rationale:** Ensures Tools provide valid, type-safe connection configuration.

**Violation Impact:** Tool instantiation fails; connection errors at runtime.

---

### BR-TOOL-002: Input Schema Completeness
**Enforcement:** API

**Category:** Validation  
**Description:** Tool `inputSchema` MUST declare every variable referenced in its `operation` definition:
- Graph queries: all Cypher parameters
- REST calls: all template variables in path/headers/body
- LLM calls: all variables in `promptTemplate` and `systemPrompt`
- MCP tools: all argument mappings

**Rationale:** Undeclared variables cause execution failures; schema serves as contract.

**Violation Impact:** Runtime errors when ProcessSteps provide incomplete inputs.

---

### BR-TOOL-003: Output Schema Validity
**Enforcement:** API

**Category:** Validation  
**Description:** Tool `outputSchema` must be valid JSON Schema that accurately describes the operation's return value structure.

**Rationale:** Downstream ProcessSteps rely on output schema for variable interpolation.

**Violation Impact:** ProcessStep interpolation fails; workflows break unpredictably.

---

### BR-TOOL-004: Deletion Safety
**Enforcement:** API

**Category:** Constraint  
**Description:** A Tool CANNOT be deleted if:
- Any ProcessStep has `toolId` referencing it
- Tool is referenced in active Process execution context

**Rationale:** Prevents orphaning ProcessSteps and breaking workflows.

**Violation Impact:** Processes become unexecutable; active executions fail.

---

### BR-TOOL-005: Disabled Tool Restrictions
**Enforcement:** Worker

**Category:** Constraint  
**Description:** Tools with `enabled=false`:
- CANNOT be scheduled by new Process executions
- Complete current executions normally
- Remain queryable for metadata/audit

**Rationale:** Allows graceful deprecation without breaking in-flight work.

**Violation Impact:** Processes fail at scheduling; user confusion.

---

### BR-TOOL-006: Service Health Requirements (UPDATED)
**Enforcement:** Worker

**Category:** Process  
**Description:** Tool execution CANNOT proceed if:
- Tool `enabled=false`, OR
- Tool `status='down'`, OR
- Service `status='down'`

Tools MAY execute with Tool or Service `status='degraded'` but MUST log warnings.

**Rationale:** Prevents operations against unavailable or misconfigured infrastructure.

**Violation Impact:** Execution failures; wasted resources.

---

### BR-TOOL-009: Tool Health Status Management
**Enforcement:** Worker

**Category:** Process  
**Description:** Tool `status` is system-managed through periodic health checks:
- `enabled=false` → status CANNOT be `healthy`
- Health checks validate: Service reachable + connectionParams valid + operation executable
- Status transitions: `healthy` ↔ `degraded` ↔ `down`
- Inherits Service status as floor (Tool cannot be healthier than Service)

**Rationale:** Tool-specific health enables precise execution decisions.

**Violation Impact:** Processes attempt operations against misconfigured Tools.

---

### BR-TOOL-010: Hierarchical Health Constraints
**Enforcement:** Worker

**Category:** Invariant  
**Description:** Tool status constrained by Service status:
- If Service `status='down'` → Tool MUST be `down`
- If Service `status='degraded'` → Tool CANNOT be `healthy`
- Tool can be unhealthy while Service is healthy (bad connectionParams)

**Rationale:** Tool health depends on underlying Service availability.

**Violation Impact:** Misleading health indicators; incorrect routing decisions.

---

### BR-TOOL-011: Health Check Frequency
**Enforcement:** Worker

**Category:** Process  
**Description:** Tool health checks:
- Triggered after Service health changes
- Scheduled independently at configurable intervals (default: 2 minutes)
- Include lightweight operation validation (e.g., test query, API ping)
- Failed checks trigger exponential backoff

**Rationale:** Balances fresh health data with system load.

**Violation Impact:** Stale health data; delayed failure detection.

---

## Process Rules

### BR-PROCESS-001: Minimum Step Requirement
**Enforcement:** API

**Category:** Invariant  
**Description:** Every Process MUST contain at least one ProcessStep.

**Rationale:** Empty Processes have no behavior and indicate configuration error.

**Violation Impact:** Process execution completes immediately with no effect; user confusion.

---

### BR-PROCESS-002: Acyclic Step Dependencies
**Enforcement:** API

**Category:** Invariant  
**Description:** ProcessStep `dependsOn` relationships CANNOT form cycles within a Process. The dependency graph must be a directed acyclic graph (DAG).

**Rationale:** Cyclic dependencies cause deadlocks during execution.

**Violation Impact:** Process execution hangs indefinitely; system resources exhausted.

---

### BR-PROCESS-003: Forward-Only Dependencies
**Enforcement:** API

**Category:** Invariant  
**Description:** A ProcessStep CANNOT depend on steps defined later in the Process step array. `dependsOn` must reference steps that appear earlier.

**Rationale:** Ensures execution order is deterministic and parseable.

**Violation Impact:** Execution order ambiguity; potential runtime errors.

---

### BR-PROCESS-004: Parallel Step Independence
**Enforcement:** API

**Category:** Invariant  
**Description:** ProcessSteps with `execution.mode='parallel'` CANNOT have `dependsOn` relationships with each other. They must be fully independent.

**Rationale:** Parallel steps execute concurrently; dependencies imply sequential ordering.

**Violation Impact:** Execution deadlocks; undefined behavior.

---

### BR-PROCESS-005: Output Variable Traceability
**Enforcement:** API

**Category:** Validation  
**Description:** Every variable referenced in Process `outputTemplate` MUST originate from either:
- `initialContext` (declared input variables), OR
- `output.variable` from some ProcessStep

**Rationale:** Undefined variables cause template rendering failures.

**Violation Impact:** Process execution completes but output generation fails.

---

### BR-PROCESS-006: Token Budget Allocation
**Enforcement:** API

**Category:** Calculation  
**Description:** If Process has `tokenBudget`:
- Sum of all ProcessStep `output.tokenBudget` values MUST NOT exceed Process `tokenBudget`
- Unspecified step budgets inherit proportional allocation from remaining budget

**Rationale:** Prevents budget overruns; ensures fair resource distribution.

**Violation Impact:** Process fails at validation; token exhaustion mid-execution.

---

### BR-PROCESS-007: Recursion Depth Limits
**Enforcement:** Worker

**Category:** Constraint  
**Description:** Process `maxRecursionDepth` limits how many times processes can call processes recursively (directly or indirectly):
- Default: 3 levels
- Maximum: 10 levels
- Exceeded depth causes execution termination with clear error

**Rationale:** Prevents infinite recursion and stack overflow scenarios.

**Violation Impact:** System instability; resource exhaustion.

---

### BR-PROCESS-008: Deletion Safety
**Enforcement:** API

**Category:** Constraint  
**Description:** A Process CANNOT be deleted if:
- Any Conversation has `processId` referencing it
- Process is referenced in active execution context

**Rationale:** Prevents orphaning Conversations and breaking active workflows.

**Violation Impact:** Conversations become unresponsive; active executions fail.

---

### BR-PROCESS-009: Enabled Tool Requirements
**Enforcement:** API

**Category:** Validation  
**Description:** All Tools referenced by ProcessSteps in an enabled Process MUST be enabled themselves.

**Rationale:** Ensures executable processes only reference executable tools.

**Violation Impact:** Process fails at step execution; cascading failures.

---

### BR-PROCESS-010: Process Ownership
**Enforcement:** API
**Category:** Access Control  
**Priority:** High  
**Applies To:** Process

**Rule:**
Process.ownerId set from authenticated user context during creation. Immutable after creation. Process owned by creating user.

**Determines access control:**
- Only owner can update/delete Process
- Only owner can execute Process directly
- Determines which Tools Process may reference (via BR-PROCESS-011)

**Validation:**
- POST /processes: ownerId = authenticated user ID from token
- PUT/DELETE /processes/{id}: ownerId must match authenticated user
- Process execution: ownerId must match executor user ID

**Violation Impact:**
403 Forbidden if user attempts to modify/execute Process they don't own.

---

### BR-PROCESS-011: Process-Tool Access Validation
**Enforcement:** API & Worker
**Category:** Access Control  
**Priority:** High  
**Applies To:** Process, ProcessStep, Tool

**Rule:**
ProcessSteps may only reference Tools where:
- Tool.ownerId = Process.ownerId (own Tool), OR
- Tool.shared = true (shared Tool accessible to Process owner)

**Validation Timing:**
- Occurs at Process creation (POST) and update (PUT)
- Also occurs at execution runtime (BR-EXEC-003)
- Rejects with 422 + list of inaccessible Tools

**Rationale:**
Process owner must have access to all Tools at construction time. Runtime check handles sharing revocation scenario.

**Validation:**
For each ProcessStep.toolId:
1. Resolve Tool entity
2. Check: Tool.ownerId = Process.ownerId OR Tool.shared = true
3. If false: Reject with 422 "Step [N] references inaccessible Tool [name]"

**Violation Impact:**
422 Unprocessable Entity with detailed list of inaccessible Tools by step number.

---

## ProcessStep Rules

### BR-STEP-001: Input Schema Conformance
**Enforcement:** API

**Category:** Validation  
**Description:** ProcessStep `inputs` map MUST conform to its target execution requirements:
- If `toolId` specified: Provide values for all required Tool `inputSchema` properties, match declared types (after interpolation), and avoid extra properties
- If `processId` specified: Provide values for all required Process `initialContext` variables, match declared types (after interpolation), and avoid extra variables
- Exactly one of `toolId` or `processId` MUST be specified

**Rationale:** Steps invoke either Tools (leaf operations) or Processes (recursive orchestration). Strong validation prevents ambiguous targets and ensures correct parameter passing.

**Violation Impact:** Missing/mismatched inputs cause execution failures; specifying both or neither target makes orchestration ambiguous.

---

### BR-STEP-002: Interpolation Variable Validity
**Enforcement:** API

**Category:** Validation  
**Description:** ProcessStep `inputs` interpolation expressions (e.g., `{step.searchResults}`) MUST reference:
- Process `initialContext` variables, OR
- `output.variable` from ProcessSteps in `dependsOn` chain

**Rationale:** Undefined variable references cause runtime interpolation failures.

**Violation Impact:** Step execution fails during input preparation.

---

### BR-STEP-003: Conditional Execution Safety
**Enforcement:** API

**Category:** Validation  
**Description:** ProcessStep `execution.condition` expressions:
- MUST be valid JavaScript boolean expressions
- Can ONLY reference variables from `initialContext` or prior step outputs
- CANNOT have side effects (pure evaluation only)

**Rationale:** Prevents execution logic from breaking due to undefined variables or unsafe operations.

**Violation Impact:** Conditional evaluation fails; step execution behavior becomes unpredictable.

---

### BR-STEP-004: Required Output Handling
**Enforcement:** Worker

**Category:** Process  
**Description:** If ProcessStep has `output.required=true`:
- Execution failure MUST halt entire Process with error
- Empty/null outputs MUST be treated as failures
- Downstream steps MUST NOT execute

**Rationale:** Critical outputs are non-negotiable; proceeding without them corrupts workflow.

**Violation Impact:** Processes continue with invalid state; data corruption.

---

### BR-STEP-005: Timeout Enforcement
**Enforcement:** Worker

**Category:** Process  
**Description:** If ProcessStep has `execution.timeout`:
- Execution exceeding timeout MUST be terminated
- Timeout handling follows `output.required` logic (fail or continue)
- Minimum timeout: 1 second; Maximum: 300 seconds (5 minutes)

**Rationale:** Prevents hung operations from blocking workflow indefinitely.

**Violation Impact:** System resources exhausted; poor UX from hanging operations.

---

### BR-STEP-006: Manual Interaction Mode
**Enforcement:** Worker

**Category:** Process  
**Description:** ProcessStep with `execution.interactionMode='manual'`:
- MUST pause Process execution and request human input
- Timeout applies to human response time
- User input becomes step output value

**Rationale:** Enables human-in-the-loop workflows for critical decisions.

**Violation Impact:** Processes complete without required human oversight.

---

### BR-STEP-007: Target Exclusivity
**Enforcement:** API

**Category:** Invariant  
**Description:** ProcessStep MUST specify exactly one execution target:
- `toolId` for invoking Tools (leaf operations)
- `processId` for invoking Processes (recursive orchestration)
- Cannot specify both
- Cannot specify neither

**Rationale:** Guarantees unambiguous execution semantics and observability.

**Violation Impact:** Ambiguous or no-op steps; Process execution cannot proceed reliably.

---

### BR-STEP-008: Recursive Process Depth
**Enforcement:** Worker

**Category:** Constraint  
**Description:** When ProcessStep invokes a Process via `processId`:
- Invocation counts toward Process `maxRecursionDepth` (default 3, max 10)
- Depth tracked across entire execution stack (Process A → B → C)
- Exceeding depth limit terminates execution with clear error referencing call stack

**Rationale:** Prevents infinite recursion and runaway resource usage while enabling compositional workflows.

**Violation Impact:** Without enforcement, recursive loops crash the system; without clear errors, debugging is impossible.

---

## Conversation Rules

### BR-CONV-001: Process Hint Validity
**Enforcement:** API

**Category:** Validation  
**Description:** Conversation `processId` (UI hint for preferred Process) MUST:
- Reference an enabled Process when present
- May be null for new conversations until user selects a Process
- Update idempotently when user creates an agent turn with a different Process

**Rationale:** processId exists to pre-populate the UI selector, not to drive execution. Keeping it aligned with enabled Processes prevents invalid defaults.

**Violation Impact:** UI defaults to unavailable Processes; user must reconfigure every turn.

---

### BR-CONV-001A: Hint Update on Agent Turn Creation
**Enforcement:** Worker

**Category:** Process  
**Description:** When the user creates a new agent turn:
- System updates `conversation.processId` to the Process selected for that turn
- Update occurs atomically with alternative creation
- Existing alternatives retain their own immutable `alternative.processId`

**Rationale:** Remembers the user’s latest Process preference so subsequent turns default accordingly.

**Violation Impact:** UI forgets user preference, forcing repetitive selections.

---

### BR-CONV-001B: Execution Source of Truth
**Enforcement:** Worker

**Category:** Invariant  
**Description:** Process execution MUST use `alternative.processId`, never `conversation.processId`:
- Regenerations run the Process recorded on the alternative being regenerated
- New alternatives capture the Process the user selected at creation
- Conversation.processId is read only for UI defaulting; execution ignores it

**Rationale:** Alternative.processId provides immutable audit trail and reproducibility. Conversation.processId may have changed since the alternative was created.

**Violation Impact:** Responses regenerate with wrong Process; audit trail becomes unreliable.

---

### BR-CONV-002: User Ownership
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Every Conversation MUST have exactly one `userId` owner, set at creation and never changed.

**Rationale:** Establishes clear data ownership and access control.

**Violation Impact:** Authorization failures; data privacy violations.

---

### BR-CONV-003: Fork Integrity
**Enforcement:** API

**Category:** Invariant  
**Description:** If Conversation has `parentConversationId`:
- Parent Conversation MUST exist
- `forkOriginTurnId` MUST reference a Turn in parent Conversation
- `forkOriginAlternativeId` MUST reference a valid alternative within that Turn
- Fork relationship is immutable (parentConversationId, forkOriginTurnId, forkOriginAlternativeId)

**Rationale:** Maintains conversation tree integrity; enables navigation and context sharing. Recording the specific alternative enables precise reconstruction of the fork point context.

**Violation Impact:** Broken references; inability to trace conversation lineage; ambiguous fork context when origin Turn has multiple alternatives.

---

### BR-CONV-004: Active Entity Synchronization
**Enforcement:** Worker

**Category:** Process  
**Description:** Conversation `activeEntities` array MUST stay synchronized with Entities having recent activity:
- Entities extracted from recent Episodes (configurable, default 10, updates asyncronously as past Entities are enriched.)
- Entities manually created or pinned by user
- Updated atomically with each new Turn

**Rationale:** Keeps conversation-level entity awareness current for context assembly.

**Violation Impact:** Outdated entity tracking; irrelevant context included.

---

### BR-CONV-005: Status Transition Rules
**Enforcement:** Worker

**Category:** Process  
**Description:** Conversation status transitions:
- `active` → `archived`: allowed anytime
- `archived` → `active`: allowed anytime
- Archived conversations can still receive turns (become active automatically)

**Rationale:** Supports flexible conversation lifecycle management.

**Violation Impact:** User confusion; inability to resume conversations.

---

### BR-CONV-006: Deletion Prohibition
**Enforcement:** Domain

**Category:** Constraint  
**Description:** Conversations are permanent audit records. They may be created and updated (metadata only) but NEVER deleted. Archival is modeled via `status='archived'` rather than physical removal; linked Graphiti Episodes, Summaries, and Introspections remain intact for compliance.

**Rationale:** Prevents orphaned knowledge-graph artifacts and preserves the full audit/history required for safety reviews.

**Violation Impact:** Catastrophic data loss; broken references across system; regulatory risk.

---

## ConversationTurn Rules

### BR-TURN-001: Immutability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** ConversationTurns are immutable after creation. No updates or deletions allowed.

**Rationale:** Preserves complete conversation history for audit and replay.

**Violation Impact:** Audit trail corruption; inability to trust conversation history.

---

### BR-TURN-002: Conversation Membership
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Every ConversationTurn MUST belong to exactly one Conversation via `conversationId`.

**Rationale:** Establishes clear containment relationship.

**Violation Impact:** Orphaned turns; broken conversation threads.

---

### BR-TURN-003: Parent Turn Validation
**Enforcement:** API

**Category:** Validation  
**Description:** If ConversationTurn has `parentTurnId`:
- Referenced Turn MUST exist and belong to same Conversation
- Parent Turn MUST have earlier `sequence` number
- Null `parentTurnId` ONLY allowed for first Turn in Conversation

**Rationale:** Maintains conversation tree structure integrity.

**Violation Impact:** Broken threading; circular references; navigation failures.

---

### BR-TURN-004: Sequence Monotonicity
**Enforcement:** Domain

**Category:** Invariant  
**Description:** ConversationTurn `sequence` numbers:
- MUST be non-negative integers
- MUST equal parent.sequence + 1 (or 1 if parentTurnId is null for root Turn)
- Siblings (Turns sharing same parentTurnId) will naturally have identical sequence numbers
- Sequence provides depth-in-tree ordering, not global conversation ordering

**Rationale:** Provides deterministic path ordering; sequence represents position along any traversal from root to leaf.

**Violation Impact:** Ambiguous turn depth; cannot determine conversation tree structure.

---

### BR-TURN-005: Speaker-Type Coherence
**Enforcement:** API

**Category:** Validation  
**Description:** ConversationTurn `speaker` and `turnType` must align:
- `speaker='user'` → `turnType='message'` only
- `speaker='agent'` → `turnType='message'` or `turnType='tool_result'`
- `speaker='system'` → `turnType='summary'` only

**Rationale:** Enforces semantic consistency in conversation structure.

**Violation Impact:** Confusing conversation display; broken assumptions in UI.

---

### BR-TURN-006: Episode Association
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Every ConversationTurn alternative MUST have valid `episodeId` referencing a Graphiti Episode with:
- Matching `group_id` (corresponds to `conversationId`)
- Matching content type for the alternative speaker
- Valid timestamp relationship (Episode.created_at == alternative.createdAt)

**Rationale:** Ties each alternative to concrete, searchable content.

**Violation Impact:** Broken semantic search; missing content for alternatives.

---

### BR-TURN-007: Process Traceability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Every alternative MUST capture immutable process provenance:
- User alternatives have `processId = null` (user input)
- Agent alternatives record the Process selected at creation; value never changes
- System alternatives reference the summarization/introspection Process

Alternative.processId is the execution source of truth. Conversation.processId is a mutable hint and may differ.

**Rationale:** Guarantees replayability, auditability, and analytics accuracy.

**Violation Impact:** Regeneration & auditing fail; cannot determine which Process produced a response.

---

### BR-TURN-008: Alternative Uniqueness
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Each ConversationTurn MUST have:
- At least one entry in `alternatives`
- Exactly one alternative with `isActive=true`
- All alternative IDs unique within the Turn

**Rationale:** Ensures deterministic display and path assembly.

**Violation Impact:** Ambiguous “current” version; context reconstruction fails.

---

### BR-TURN-009: Alternative Input Context Requirement
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Each alternative MUST carry valid input context:
- If Turn has `parentTurnId` (non-root), `inputContext.parentAlternativeId` MUST reference a valid alternative in that parent Turn.
- If Turn is root (`parentTurnId=null`), `inputContext.parentAlternativeId` MUST be null.

**Rationale:** Identifies which parent alternative was responded to while Turn.parentTurnId remains the single source of truth for structural parentage.

**Violation Impact:** Cannot determine which parent alternative produced the input; provenance and cache logic break.

---

### BR-TURN-010: Alternative Content Requirements
**Enforcement:** Domain

**Category:** Validation  
**Description:** Every alternative MUST include:
- Valid `episodeId`
- `createdAt` timestamp
- For agent alternatives: enabled `processId`
- For user alternatives: `processId=null`

**Rationale:** Guarantees alternatives are auditable artifacts.

**Violation Impact:** Missing content; cannot display or regenerate.

---

### BR-TURN-011: Active Alternative Switching
**Enforcement:** Worker

**Category:** Process  
**Description:** When the user selects a different alternative in the UI:
- Previous active alternative’s `isActive` is set to `false`
- Newly selected alternative’s `isActive` is set to `true`
- System recomputes child Turn cache status by comparing each child alternative’s `inputContext.parentAlternativeId` to the new active alternative

**Rationale:** `isActive` mirrors on-screen selection. Cache indicators update to reflect whether descendants match what the user now sees.

**Violation Impact:** UI shows wrong alternative; cache indicators drift from actual selection.

---

### BR-TURN-012: User Alternative Creation
**Enforcement:** Worker

**Category:** Process  
**Description:** When user edits content:
- Create new alternative with new Episode
- Append to Turn’s `alternatives`
- If `makeActive=true`, switch active alternative atomically
- Preserve previous alternatives (no deletion)

**Rationale:** Enables prompt revision without context pollution.

**Violation Impact:** Users forced into correction chains; audit trail lost.

---

### BR-TURN-013: Agent Alternative Generation
**Enforcement:** Worker

**Category:** Process  
**Description:** Agent alternatives are created when user:
- Requests different Process for same input
- Regenerates using same Process
- Continues from different parent alternative

Each alternative records `processId` and `createdAt`.

**Rationale:** Supports Process comparison and regeneration workflows.

**Violation Impact:** Cannot explore different Process behaviors.

---

### BR-TURN-014: Cache Status Derivation
**Enforcement:** Worker

**Category:** Calculation  
**Description:** Agent alternative cache status derives from comparing stored input context to the parent’s current display state:
```typescript
if (turn.speaker === 'user') {
  cacheStatus = 'valid';
} else if (alternative.episodeId === null) {
  cacheStatus = 'generating';
} else if (!turn.parentTurnId) {
  cacheStatus = 'valid';  // Root alternatives have no parent to compare
} else {
  const parentTurn = getTurn(turn.parentTurnId);
  const parentActive = parentTurn?.alternatives.find(a => a.isActive)?.id;
  cacheStatus = alternative.inputContext.parentAlternativeId === parentActive
    ? 'valid'
    : 'stale';
}
```

User alternatives always read as `valid` because they are the source input.

**Rationale:** Cache status is feedback telling the user whether this response matches what’s currently on screen upstream.

**Violation Impact:** Users misinterpret stale responses as current; incorrect regeneration decisions.

---

## Episode Rules

### BR-EPISODE-001: Immutability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Episodes are immutable after creation by Graphiti. No updates or deletions through application layer.

**Rationale:** Preserves semantic search index integrity; audit trail.

**Violation Impact:** Search index corruption; lost conversation content.

---

### BR-EPISODE-002: Group ID User Scoping
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Episode `group_id` MUST equal the `userId` of the owning Conversation:
- All Episodes within user scope share same group_id
- Semantic search filters by group_id to maintain user isolation
- Cross-user Episode access prohibited

**Rationale:** User-scoped knowledge enables agent learning across conversations while maintaining privacy boundaries. Each user trains their own agent persona.

**Violation Impact:** Privacy violation; cross-user knowledge contamination; broken semantic search isolation.

---

### BR-EPISODE-003: Content Size Management via Fork Architecture
**Enforcement:** Worker

**Category:** Process  
**Description:** Content size naturally bounded through conversation forking:
- User messages: Included verbatim in main conversation thread
- Agent responses: Included verbatim in main conversation thread
- Tool invocations: Spawn forked conversation where tool execution occurs
  - Fork contains: tool invocation details, raw tool results, LLM processing, multi-step reasoning
  - Fork final response: Concise synthesis (e.g., "Pancakes")
  - Main thread receives: Only the concise final response from fork
  - Fork preserved for audit but not included in main thread WorkingMemory

**Rationale:** Fork pattern naturally contains content size in main thread while preserving complete audit trail in fork. Main thread remains concise and focused; detailed tool execution isolated in side branches.

**Violation Impact:** If tool results included in main thread: storage bloat, context pollution, slow semantic search. If forks not preserved: lost audit trail, cannot debug tool execution.

---

### BR-EPISODE-004: Name Brevity
**Enforcement:** Worker

**Category:** Validation  
**Description:** Episode `name` should be concise summary (max 100 chars) suitable for display, not verbatim content.

**Rationale:** Enables efficient episode browsing and selection.

**Violation Impact:** Cluttered UI; poor UX.

---

## Entity Rules

### BR-ENTITY-001: Source Provenance
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Every Entity MUST track all sources in `sources` array:
- User-created entities: source type='user' with created_by userId
- Graphiti-extracted entities: source type='graphiti' with episode_id
- Enrichment-enhanced entities: source type='enrichment' with process_id
- Merged entities preserve ALL sources from both original entities

**Rationale:** Maintains complete audit trail of entity provenance; enables trust evaluation.

**Violation Impact:** Lost provenance; cannot determine entity reliability.

---

### BR-ENTITY-002: User Creation Requirements
**Enforcement:** API

**Category:** Validation  
**Description:** User-created entities MUST have:
- Non-empty name (after sanitization)
- Basic summary/description
- Optional category from core set (Person, Organization, Project, Concept, Object, Event, Place)
- Created with source='user' and valid userId

**Rationale:** Ensures minimum viable entity definition for immediate use.

**Violation Impact:** Ambiguous entities; poor context quality.

---

### BR-ENTITY-003: Deduplication Preservation
**Enforcement:** Worker

**Category:** Invariant  
**Description:** When Graphiti deduplicates entities:
- Merged entity MUST preserve all sources from both entities
- User-created entity UUID takes precedence
- All fact_ids and entity_edge_ids merged (deduplicated)
- Best name chosen (user-provided takes precedence over AI-extracted)
- Summaries combined or best selected

**Rationale:** Preserves complete entity history through merges.

**Violation Impact:** Lost entity lineage; broken references.

---

### BR-ENTITY-004: Enrichment Append-Only
**Enforcement:** Worker

**Category:** Invariant  
**Description:** Enrichment process MUST:
- Only add to facets and enrichment fields
- Never remove or modify sources array
- Never delete fact_ids or entity_edge_ids
- Store enrichment with timestamp and process_id
- Record confidence scores for all inferred facets

**Rationale:** Enrichment enhances entities without corrupting provenance.

**Violation Impact:** Lost source information; cannot audit enrichment quality.

---

### BR-ENTITY-005: Category Stability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Entity category (Person, Organization, Project, Concept, Object, Event, Place):
- User-set category is immutable unless user changes it
- AI-inferred category has confidence score
- Deduplication preserves user category over AI category
- Category changes tracked in sources with type='user' modification

**Rationale:** User-provided categorization is authoritative.

**Violation Impact:** Category thrashing; user intent overridden.

---

### BR-ENTITY-006: Immediate Availability
**Enforcement:** Worker

**Category:** Process  
**Description:** User-created entities MUST be:
- Immediately added to Conversation.activeEntities
- Immediately available in WorkingMemory for current turn
- Created in Graphiti before Turn processing begins
- No waiting for AI extraction or enrichment

**Rationale:** User-created entities provide immediate context, not eventual.

**Violation Impact:** User expects entity in context but it's missing; poor UX.

---

### BR-ENTITY-007: Facet Discovery
**Enforcement:** Worker

**Category:** Process  
**Description:** Enrichment process MAY discover new facet dimensions:
- Emergent facets stored with confidence scores
- No predefined facet schema required
- Common facets across entities indicate useful dimensions
- User can view and correct facet assignments

**Rationale:** Faceted typing emerges from actual usage patterns.

**Violation Impact:** Rigid taxonomy prevents natural semantic discovery.

---

### BR-ENTITY-008: User Scope Isolation
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Entity `group_id` MUST equal `userId` of creating/extracting user:
- User-created entities: group_id set to creating user's userId
- Graphiti-extracted entities: group_id set to userId of conversation where extracted
- Deduplication only merges entities within same group_id (same user)
- Cross-user entity references prohibited

**Rationale:** Entities are user-scoped knowledge; users build independent knowledge graphs.

**Violation Impact:** Privacy violation; entity contamination across users; incorrect deduplication.

---

## WorkingMemory Rules

### BR-MEMORY-001: Singleton Per Conversation
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Each Conversation has exactly ONE WorkingMemory instance, created with Conversation and deleted only when Conversation is deleted.

**Rationale:** Establishes clear memory ownership; prevents duplication.

**Violation Impact:** Inconsistent memory state; wasted storage.

---

### BR-MEMORY-002: Immediate Path from Active Alternatives
**Enforcement:** Worker

**Category:** Process  
**Description:** WorkingMemory MUST maintain:
- `immediatePath`: Array of `{turnId, alternativeId, episodeId}` tuples produced by traversing `isActive` alternatives (the path the user currently has on screen) from `currentTurnId:currentAlternativeId` back to root, limited to last N turns (default 10)
- `activeEntities`: Entities from Conversation.activeEntities PLUS entities mentioned in `immediatePath` Episodes
- Path recomputed whenever the user changes which alternatives are active or when new Turns are added

**Rationale:** Context assembly mirrors the user’s visible conversation path; system never substitutes its own canonical path.

**Violation Impact:** Agent responds to different history than user sees; mental model breaks.

---

### BR-MEMORY-003: Token Budget Accuracy
**Enforcement:** Worker

**Category:** Calculation  
**Description:** WorkingMemory `totalTokens` MUST equal:
```
sum(tokens(immediatePath Episodes)) + 
sum(tokens(summaries)) + 
sum(tokens(activeEntities with inclusion flags applied))
```

Where `immediatePath` only contains Episodes from active alternatives along the current path and activeEntities token calculation respects inclusion flags.

**Rationale:** Token budget matches actual prompt content.

**Violation Impact:** Context overruns; prompt truncation; unexpected costs.

---

### BR-MEMORY-004: Reference Validity
**Enforcement:** Domain

**Category:** Invariant  
**Description:** All IDs in WorkingMemory (`immediateEpisodes`, `summaries`) MUST reference entities belonging to the same Conversation.

**Rationale:** Prevents cross-conversation contamination.

**Violation Impact:** Agent receives irrelevant context; privacy leakage.

## Summary Rules

### BR-SUMMARY-001: Summary Lifecycle & Mutability
**Enforcement:** Domain

**Category:** Invariant  
**Description:**
- **Created:** Worker compression process OR admin manual override (POST)
- **Updated:** Content editable via PUT for emergency repair
- **Deleted:** Deletable via DELETE; may trigger recompression consideration
- **Immutable Fields:** `id`, `conversationId`, `episodeId` (original), `priorTurnId`, `createdAt`, `createdBy`

**Update Semantics:**
- PUT does NOT modify Episode content directly
- PUT replaces `episodeId` pointer to NEW Episode containing corrected content
- Original Episode remains in Graphiti for audit trail

**Deletion Semantics:**
- Deletion publishes SummaryDeletionRequested event
- Worker evaluates if recompression needed (context now under-compressed)

**Rationale:** Enables emergency repair without rewriting history; preserves provenance of original summary Episode.

**Violation Impact:** Inability to correct bad summaries or audit historical changes.

---

### BR-SUMMARY-002: Source Episode Requirements
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Summary MUST reference at least one source Episode via `sourceEpisodeIds`, and all source Episodes MUST:
- Belong to same user as Summary (matching group_id)
- Have `compressionLevel` less than this Summary's `compressionLevel`

**Rationale:** Ensures compression hierarchy integrity within user scope.

**Violation Impact:** Cross-user contamination; compression hierarchy violation.

---

### BR-SUMMARY-003: Compression Level Calculation
**Enforcement:** Domain

**Category:** Calculation  
**Description:** Summary `compressionLevel` MUST equal:
```
max(compressionLevel of sourceEpisodes) + 1
```
Where original Episodes have `compressionLevel = 0`.

**Rationale:** Maintains compression hierarchy; enables depth tracking.

**Violation Impact:** Incorrect compression trees; infinite compression loops.

---

### BR-SUMMARY-004: Content Episode Requirement
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Summary `episodeId` MUST reference a Graphiti Episode with:
- `source='summary'`
- `group_id` matching Summary `userId` (same as source Episodes)
- Content representing compressed version of source Episodes

**Rationale:** Ensures summaries are searchable and retrievable like other Episodes.

**Violation Impact:** Summaries not searchable; broken memory retrieval.

---

### BR-SUMMARY-005: Creation Traceability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Summary `createdBy` MUST record the `processId` that performed compression.

**Rationale:** Process definitions capture compression workflows; internal Tool usage is an implementation detail.

**Violation Impact:** Cannot trace which Process generated a summary; compression quality issues untraceable.

---

## Turn-Episode Content Storage

### BR-TURN-EPISODE-001: Permanent Content Storage
**Enforcement:** Domain

**Category:** Invariant  
**Description:** `Turn.content` is permanently stored and NEVER deleted, regardless of Episode sync status. Both Turn and Episode maintain full content for their respective purposes.

**Rationale:** Turn.content serves the display layer; Episode.content powers semantic/knowledge operations. Intentional duplication simplifies design and removes archival logic.

**Violation Impact:** Reintroduces deleted code paths, complicates display vs knowledge responsibilities.

### BR-TURN-EPISODE-002: Episode Name Uniqueness
**Enforcement:** Worker

**Category:** Constraint  
**Description:** Episode names MUST embed Turn UUID using format `Turn:{turn.uuid}` to enable reliable matching during polling.

**Rationale:** Graphiti assigns Episode UUID asynchronously; embedding Turn UUID allows polling worker to correlate Episode to Turn.

**Violation Impact:** Polling worker cannot correlate Episodes; sync stuck in pending state.

### BR-TURN-EPISODE-003: UI Content Source
**Enforcement:** Domain

**Category:** Constraint  
**Description:** UI components MUST render `Turn.content` directly; NEVER fetch content from Graphiti Episodes.

**Rationale:** Display layer remains decoupled from Graphiti; avoids unnecessary latency and coupling.

**Violation Impact:** Slower UI and brittle dependency on Graphiti for rendering.

---

### BR-SUMMARY-006: Compression Counter Synchronization
**Enforcement:** Worker

**Category:** Process  
**Description:** When Summary is created:
- Increment CompressionCounter.compressionCount for the Conversation
- Check if `(compressionCount - lastIntrospectionAt) >= triggerThreshold`
- If threshold reached, trigger async introspection process
- Counter updates are atomic with Summary creation

**Rationale:** Ensures introspection triggers reliably at configured intervals.

**Violation Impact:** Missed introspection opportunities; counter desynchronization.

---

## Introspection Rules

### BR-INTRO-001: Introspection Mutability & Carousel Management
**Enforcement:** Domain

**Category:** Invariant  
**Description:**
- **Created:** Introspection worker process OR user manual injection (POST)
- **Updated:** Content editable via PUT for persona correction
- **Deleted:** Deletable via DELETE; triggers carousel rebalancing
- **Immutable Fields:** `id`, `userId`, `position`, `createdAt`, `createdBy`

**Carousel Rules:**
- Positions 0-9 available per user (user-scoped via `group_id = userId`)
- Position immutable after creation; to move: DELETE + POST at new position
- Deletion triggers position rebalancing (higher positions shift down)

**Update Semantics:**
- PUT does NOT modify Episode content directly
- PUT replaces `episodeId` pointer to NEW Episode containing corrected content
- Original Episode remains in Graphiti for audit trail

**User Creation (POST):**
- User may manually inject introspection at specific carousel position
- If position occupied, request fails with 409 Conflict
- `createdBy` set to "user" to distinguish from worker-created

**Rationale:** Allows persona corrections while preserving carousel integrity and provenance.

**Violation Impact:** Carousel corruption, inability to correct harmful introspections, or loss of audit trail.

---

### BR-INTRO-002: Carousel Size Constraint
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Each user has one introspection carousel with fixed size `maxRotation` (default 10):
- Carousel scoped by `userId` (each user has independent carousel)
- Positions numbered 0 to maxRotation-1 within user scope
- New introspection replaces note at next position (cyclic rotation: 0→1→...→9→0)
- Replaced notes archived with full history preserved
- Agent warned which position will be replaced and chooses how to preserve information

**Rationale:** Maintains bounded working set per user while preserving complete history; agent manages information preservation creatively within user's knowledge domain.

**Violation Impact:** Memory bloat if unbounded; lost developmental context if history not preserved; carousel collision across users if not scoped.

---

### BR-INTRO-003: Position Validity
**Enforcement:** API

**Category:** Validation  
**Description:** Introspection `carouselPosition` MUST be in range [0, maxRotation-1] and correspond to its position in active carousel.

**Rationale:** Enables deterministic carousel rotation.

**Violation Impact:** Position conflicts; carousel corruption.

---

### BR-INTRO-004: Asynchronous Execution with User-Scoped Context
**Enforcement:** Worker

**Category:** Process  
**Description:** Introspection generation:
- MUST NOT block user-facing conversation operations
- Triggered when `(compressionCount - lastIntrospectionAt) >= introspectionCompressionThreshold` per user
- Agent receives:
  - **Warning:** Position X will be replaced
  - Semantic search access scoped to `userId` by default:
    - All introspection Episodes (current carousel + archived history) for this user
    - All conversation Episodes for this user
    - All Summaries for this user
  - Recent compression event context (last N summaries) for this user
  - Full tool access (semantic search, Cypher queries) within user scope
  - Extended time budget (no user blocking)
- Agent chooses:
  - How to preserve vital information from position X
  - Whether to update other positions
  - How to reorganize themes across carousel
  - What new insights to surface from entity relationships
- Creates new Episode in Graphiti with `group_id = userId`
- Failures logged but do not affect conversation flow
- After completion, updates `lastIntrospectionAt = compressionCount` for this user

**Rationale:** User-scoped semantic search enables agent to reflect across all user's conversations, building coherent long-term understanding. Each user gets personalized agent development.

**Violation Impact:** Agent cannot learn across conversations if scope too narrow; privacy violation if scope crosses users.

---

### BR-INTRO-005: Episode Content Requirement
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Introspection `episodeId` MUST reference a Graphiti Episode with:
- `source='introspection'`
- `group_id = userId` (introspections scoped to user, enabling agent learning across user's conversations)
- Content representing the reflection text
- Entity extraction and temporal facts managed by Graphiti

**Rationale:** Enables semantic search across all introspections (active carousel + archives); entity extraction captures conceptual evolution.

**Violation Impact:** Cannot semantically search introspections; lost insight discovery; no entity/relationship tracking in reflections.

---

## Metric Rules

### BR-METRIC-001: Definition Immutability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Once created, MetricDefinition `scope` and `dataType` are immutable. Other properties may be updated.

**Rationale:** Prevents type mismatches and scope confusion in historical data.

**Violation Impact:** Invalid aggregations; broken analytics queries.

---

### BR-METRIC-002: Scope-Entity Alignment
**Enforcement:** Worker

**Category:** Validation  
**Description:** MetricValue `entityId` MUST reference an entity of the type specified in MetricDefinition `scope`:
- `scope='Service'` → entityId must be valid Service ID
- `scope='Tool'` → entityId must be valid Tool ID
- etc.

**Rationale:** Ensures metrics are correctly attributed to entities.

**Violation Impact:** Broken metric queries; incorrect dashboards.

---

### BR-METRIC-003: Value Type Conformance
**Enforcement:** Worker

**Category:** Validation  
**Description:** MetricValue `value` MUST conform to MetricDefinition `dataType`:
- `integer` → whole numbers only
- `float` → decimal numbers
- `boolean` → true/false only
- `timestamp` → ISO 8601 datetime strings

**Rationale:** Enables reliable aggregations and comparisons.

**Violation Impact:** Aggregation failures; incorrect calculations.

---

### BR-METRIC-004: Retention Enforcement
**Enforcement:** Worker

**Category:** Process  
**Description:** If MetricDefinition has `retentionDays`:
- MetricValues older than retentionDays MUST be archived/deleted
- Deletion happens asynchronously via background job
- Aggregated summaries may be preserved beyond retention

**Rationale:** Manages storage costs while preserving useful aggregates.

**Violation Impact:** Storage exhaustion; performance degradation.

---

### BR-METRIC-005: Append-Only Values
**Enforcement:** Domain

**Category:** Invariant  
**Description:** MetricValues are append-only. No updates or deletions (except retention-based cleanup).

**Rationale:** Preserves accurate time-series data for analytics.

**Violation Impact:** Lost historical data; incorrect trend analysis.

---

## Cross-Entity Rules

### BR-CROSS-001: Enabled Entity Graph Consistency
**Enforcement:** Worker

**Category:** Invariant  
**Description:** For Process execution to succeed, entire dependency chain must be enabled:
- Process.enabled = true
- All ProcessSteps reference enabled Tools
- All Tools reference enabled Services
- All Services have status ≠ 'down'

**Rationale:** Prevents execution attempts against unavailable infrastructure.

**Violation Impact:** Cascading execution failures; poor UX.

---

### BR-CROSS-002: Deletion Cascade Order
**Enforcement:** Worker

**Category:** Process  
**Description:** Entity deletion must respect dependency order:
1. Conversations (requires all references cleared)
2. Processes (requires no Conversation references)
3. Tools (requires no ProcessStep references)
4. Services (requires no Tool references)
5. Secrets (requires no Tool references)

**Rationale:** Prevents orphaned references and broken relationships.

**Violation Impact:** Data integrity violations; system instability.

---

### BR-CROSS-003: Token Budget Hierarchical Consistency
**Enforcement:** Worker

**Category:** Calculation  
**Description:** Token budget constraints form hierarchy:
```
Process.tokenBudget >= sum(ProcessStep.output.tokenBudget)
Conversation.contextBudget >= WorkingMemory.totalTokens
```

**Rationale:** Prevents budget overruns at any level.

**Violation Impact:** Unexpected costs; context truncation; execution failures.

---

### BR-CROSS-004: Temporal Ordering Consistency
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Timestamps must be consistent across related entities:
- ConversationTurn.timestamp <= WorkingMemory.lastUpdated
- Episode.created_at == ConversationTurn.timestamp
- Summary.createdAt > all sourceEpisode timestamps

**Rationale:** Maintains temporal causality across system.

**Violation Impact:** Confusing timelines; broken audit trails.

---

### BR-CROSS-005: Namespace Isolation
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Certain entities must respect namespace/scope boundaries:
- Episodes: scoped to Conversation via `group_id`
- WorkingMemory: exclusive to owning Conversation
- Summaries: reference only same-Conversation Episodes
- Entities: may span conversations (global in Graphiti) but Conversation.activeEntities scopes relevance

**Rationale:** Prevents data contamination while allowing entities to connect across conversation boundaries for cross-conversation insights.

**Violation Impact:** Cross-conversation contamination in some cases; inability to connect related conversations in others.

---

## Idempotency Rules

### BR-IDEMP-001: Key Requirements
**Enforcement:** Cross-Cutting

**Category:** Invariant  
**Description:** All mutating API requests (POST/PUT/DELETE) MUST include `Idempotency-Key` header with client-generated UUID.

**Rationale:** Enables safe retries on network failures or timeouts without duplicate operations.

**Violation Impact:** Request rejected with 400 Bad Request; client cannot safely retry.

---

### BR-IDEMP-002: Key Scoping
**Enforcement:** Cross-Cutting

**Category:** Invariant  
**Description:** Idempotency keys are scoped per authenticated user:
- Different users may reuse the same key for unrelated operations
- The same user MUST NOT reuse a key for different operations within retention window

**Rationale:** Prevents cross-user collisions while preserving per-user idempotency.

**Violation Impact:** User receives another user’s cached response; data leakage.

---

### BR-IDEMP-003: Key Retention
**Enforcement:** Cross-Cutting

**Category:** Process  
**Description:** Idempotency keys stored for 24 hours after operation completion:
- Duplicate requests within 24 hours return cached response (200 OK)
- Keys expire after 24 hours and may be reused
- Retention period is fixed, not configurable

**Rationale:** Balances retry safety with storage efficiency.

**Violation Impact:** Too-short retention treats valid retries as new operations; too-long retention bloats storage.

---

### BR-IDEMP-004: Payload Consistency
**Enforcement:** Cross-Cutting

**Category:** Validation  
**Description:** Duplicate requests with same key MUST have identical request body:
- Different payload → Reject with 409 Conflict
- Same payload → Return original response with 200 OK (not 202)
- Headers (except Authorization) ignored for consistency check

**Rationale:** Prevents client bugs where retries mutate payloads.

**Violation Impact:** Inconsistent data if diverging retries are accepted.

---

### BR-IDEMP-005: Async Operation Behavior
**Enforcement:** Cross-Cutting

**Category:** Process  
**Description:** For async operations (202 Accepted responses):
- First request → Create operation, enqueue job, return 202 with operationId
- Duplicate request → Return 200 OK with same operationId (job not re-enqueued)
- Client polls `/operations/{operationId}` for status regardless

**Rationale:** Prevents duplicate background jobs while preserving async semantics.

**Violation Impact:** Duplicate jobs waste resources; inconsistent state.

---

## Alternative Management Rules

### BR-ALT-001: Alternative Immutability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Once created, an alternative’s `id`, `episodeId`, `processId`, and `createdAt` are immutable. Only `isActive` may change, and alternatives cannot be deleted.

**Rationale:** Preserves full history of attempts per conversation position.

**Violation Impact:** Lost audit trail; cannot review prior iterations.

---

### BR-ALT-002: Active Alternative Uniqueness and Cascade
**Enforcement:** Worker

**Category:** Invariant  
**Description:** Each Turn MUST always have exactly one `isActive=true` alternative. Selecting an alternative triggers a three-phase cascade:
1. **Atomic local update:** Selected alternative set `isActive=true`; previous active alternative set `isActive=false`.
2. **Ancestor cascade:** Recursively walk up to root following each alternative’s `inputContext.parentAlternativeId`; in every ancestor Turn, activate the referenced alternative and deactivate all siblings so the active path to root is coherent.
3. **Descendant invalidation:** Recursively walk down to leaves; for each descendant alternative whose `inputContext.parentAlternativeId` does not match the newly-active parent alternative, set `cacheStatus='stale'` (do NOT change `isActive`). Alternatives whose parent matches remain valid.

**Rationale:** Guarantees a single coherent active path from root to the currently selected Turn while preserving off-path alternatives for future exploration.

**Violation Impact:** Missing ancestor cascade breaks WorkingMemory traversal; missing descendant invalidation hides stale responses; skipping atomic update leaves Turns with zero or multiple active alternatives; auto-switching descendants removes user control.

---

### BR-ALT-003: Input Context Immutability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Each alternative’s `inputContext.parentAlternativeId` is immutable after creation.

**Rationale:** Locks in which parent alternative produced the input so provenance and cache status remain trustworthy.

**Violation Impact:** Cache derivation meaningless; audit trail compromised.

---

### BR-ALT-004: Lazy Regeneration
**Enforcement:** Worker

**Category:** Process  
**Description:** Agent alternatives with `cacheStatus='stale'` are regenerated only on explicit user/system request (e.g., “Regenerate response”), not automatically when parent alternative changes.

**Rationale:** Focuses compute on active tip; avoids expensive cascades.

**Violation Impact:** Wasted computation; noisy regenerations users did not ask for.

---

### BR-ALT-005: Child Alternative Creation
**Enforcement:** Worker

**Category:** Process  
**Description:** Continuing a conversation from a Turn uses:
- Existing child Turn if it already references the active parent alternative (its alternatives’ `inputContext.parentAlternativeId` already matches)
- Otherwise, create a new child Turn whose first alternative records `inputContext.parentAlternativeId` equal to the currently active parent alternative

Multiple child Turns may exist targeting different parent alternatives.

**Rationale:** Enables exploration of parallel paths (“what if I had said X”).

**Violation Impact:** Users forced down single timeline; alternative exploration impossible.

---

### BR-ALT-006: Alternative Display Ordering
**Enforcement:** Domain

**Category:** Presentation  
**Description:** UI MUST show active alternative prominently with other alternatives ordered newest-first, including metadata (Process name, timestamp, cache status).

**Rationale:** Helps users understand available attempts and their freshness.

**Violation Impact:** Confusing UI; stale alternatives mistaken for current.

---

### BR-ALT-006A: Tree Navigation Cascade Effects
**Enforcement:** Worker

**Category:** Process  
**Description:** Navigating the conversation tree (focusing a Turn, cycling alternatives, or jumping to ancestors/descendants) MUST trigger the BR-ALT-002 three-phase cascade across the tree:
- **Upward:** Recursively activate required ancestor alternatives so selected Turn is connected to root via a single active path
- **Downward:** Mark descendant alternatives `cacheStatus='stale'` if their parent alternative no longer matches; do NOT auto-switch descendant `isActive`
- **Siblings:** No effect on sibling branches; they retain own active alternatives
- **WorkingMemory:** After cascade completes, rebuild WorkingMemory so `immediatePath` reflects new active path

**Rationale:** Ensures user navigation produces coherent active paths and visible indicators for off-path responses while preserving exploration history.

**Violation Impact:** Active path ambiguity, stale context provided to agent, or unexpected auto-switching of descendant alternatives.

---

## Execution Context Rules

### BR-EXEC-001: Process Execution Atomicity
**Enforcement:** Worker

**Category:** Process  
**Description:** Process execution produces atomic results:
- All ProcessSteps complete OR entire Process fails
- Partial state is not committed to Conversation
- Rollback on failure restores pre-execution state

**Rationale:** Prevents partial/corrupt conversation state.

**Violation Impact:** Data corruption; inconsistent conversation history.

---

### BR-EXEC-002: Execution Context and Resource Accounting
**Enforcement:** Worker
**Category:** Resource Management  
**Priority:** High  
**Applies To:** Process execution, Tool execution

**Rule:**
Process execution resource accounting determined by Secret ownership:

**Scenario 1: Tool requires Secret (Tool.requiresSecret = true)**
- Tool.connectionParams.secretId identifies Secret
- Secret.userId determines execution context
- Secret owner's tokens consumed
- Secret owner's rate limits apply
- Secret owner's API quotas decremented

**Scenario 2: Tool requires no Secret (Tool.requiresSecret = false)**
- Process executor provides credentials in Tool.connectionParams
- Executor's tokens consumed
- Executor's rate limits apply
- Executor's API quotas decremented

**Scenario 3: Shared Tool with original owner's Secret**
- User A creates Tool (requiresSecret=true, connectionParams.secretId=SecretA)
- User A shares Tool (shared=true)
- User B executes via Process
- **User A pays** (Secret owner)
- User B provides Process context but User A pays infrastructure costs

**Security Implication:**
Sharing Tool with Secret delegates token/quota costs to Secret owner. Share carefully.

**Cross-Reference:**
BR-SECRET-002B ensures Secret.userId aligns with Tool.ownerId or Conversation.userId, preventing cross-user Secret usage without permission.

**Validation:**
None at configuration time. Token consumption tracked during execution.

**Violation Impact:**
N/A - defines accounting model, not a constraint.

---

### BR-EXEC-003: Process Execution Validation (Runtime)
**Enforcement:** Worker
**Category:** Execution Safety  
**Priority:** Critical  
**Applies To:** Process execution, ProcessStep execution

**Rule:**
At Process execution time, validate all resource dependencies:

**Tool Access Validation:**
For each ProcessStep Tool reference:
1. Tool must exist in database
2. Tool.ownerId = executor.userId (own Tool), OR
3. Tool.shared = true (currently shared)

**Failure Scenarios (all return 422 Unprocessable Entity):**
- Tool not found: "Tool [id] does not exist"
- Tool not shared: "Tool [name] owned by [user] is not shared"
- Tool access revoked: "Tool [name] access revoked by owner"

**Secret Validation (if Tool.requiresSecret = true):**
1. Secret must exist
2. Secret.userId = Tool.ownerId OR Secret.userId = executor.userId
3. Secret credentials must be valid (validated during API call)

**Failure Scenarios:**
- Secret not found: "Tool [name] references non-existent Secret [id]"
- Secret revoked: "Secret [name] no longer accessible"
- Invalid credentials: Runtime API error (logged, surfaced to user)

**External Dependency Failures:**
- API unavailable: Network timeout (logged, surfaced)
- Invalid credentials: 401/403 from external API (logged, surfaced)
- Rate limits: 429 from external API (logged, may retry)

**Design Principle:**
All dependency failures produce clear diagnostics. User sees specific reason for failure and suggested remediation. Internal breaks (unsharing) indistinguishable from external breaks (revoked secrets, API changes) - both handled identically.

**Validation:**
Occurs immediately before each ProcessStep execution. No caching of access checks.

**Violation Impact:**
Process execution halts at failing step with 422 + detailed error message. Subsequent steps not executed. Failure logged for diagnostics.

---

### BR-EXEC-004: Parallel Execution Isolation
**Enforcement:** Worker

**Category:** Process  
**Description:** Parallel ProcessSteps execute in isolation:
- Cannot modify shared state during execution
- Results collected atomically after all complete
- Failures handled independently per step

**Rationale:** Prevents race conditions and nondeterministic behavior.

**Violation Impact:** Data corruption; unpredictable results.

---

### BR-EXEC-005: Timeout Behavior Determinism
**Enforcement:** Worker

**Category:** Process  
**Description:** When ProcessStep times out:
- If `output.required=true`: entire Process fails immediately
- If `output.required=false`: step returns null, Process continues
- Timeout handling is deterministic and documented

**Rationale:** Ensures predictable failure modes.

**Violation Impact:** Nondeterministic failures; difficult debugging.

---

### BR-EXEC-006: Error Propagation Clarity
**Enforcement:** Worker

**Category:** Process  
**Description:** Execution errors must propagate with clear context:
- Which Process was executing
- Which ProcessStep failed
- Which Tool was invoked
- Which Service was targeted
- Original error message preserved

**Rationale:** Enables effective debugging and observability.

**Violation Impact:** Cannot diagnose failures; poor developer experience.

---

### BR-EXEC-007: Recursion Depth Tracking
**Enforcement:** Worker

**Category:** Process  
**Description:** System must track and enforce recursion depth:
- Current depth accessible in execution context
- Depth checked before each recursive Process invocation
- Clear error message on depth limit violation

**Rationale:** Prevents stack overflow and resource exhaustion.

**Violation Impact:** System crashes; resource exhaustion.

---

## Observability Rules

### BR-OBS-001: Execution Trace Completeness
**Enforcement:** Worker

**Category:** Invariant  
**Description:** Every Process execution must produce complete trace:
- Start timestamp and initiating trigger
- Each ProcessStep invocation with inputs/outputs
- All Tool calls with parameters and results
- Final Process output or failure reason
- Total execution time and resource consumption

**Rationale:** Enables debugging, optimization, and accountability.

**Violation Impact:** Cannot debug failures; lost observability.

---

### BR-OBS-002: Metric Recording Consistency
**Enforcement:** Worker

**Category:** Process  
**Description:** Metrics must be recorded consistently:
- All executions record configured metrics
- Failures do not prevent metric recording
- Metrics include both success and failure cases
- Timestamps accurate to millisecond precision

**Rationale:** Ensures reliable analytics and monitoring.

**Violation Impact:** Incomplete data; misleading dashboards.

---

### BR-OBS-003: Health Check Frequency
**Enforcement:** Worker

**Category:** Process  
**Description:** Services must be health-checked on regular intervals:
- Minimum interval: 30 seconds
- Maximum interval: 5 minutes
- Failed checks trigger exponential backoff
- Status updates propagated immediately

**Rationale:** Balances freshness with system load.

**Violation Impact:** Stale status information; delayed failure detection.

---

## Security Rules

### BR-SEC-001: Secret Access Control (UPDATED)
**Enforcement:** Cross-Cutting

**Category:** Invariant  
**Description:** Secrets can only be accessed by:
- Owning user (via `userId` match) in their own Conversations/Tools
- System processes acting on user's behalf with impersonation context
- Admin users with explicit audit logged access grant

User A cannot access User B's secrets under any circumstances.

**Rationale:** Minimizes credential exposure surface; enforces user ownership boundaries.

**Violation Impact:** Security vulnerability; multi-tenant isolation breach; credential leakage.

---

### BR-SEC-002: Conversation Isolation
**Enforcement:** Cross-Cutting

**Category:** Invariant  
**Description:** Conversations and their data (Turns, WorkingMemory, Episodes) accessible only by:
- Owning user (via `userId`)
- System processes acting on user's behalf
- Admin users with explicit access grant

**Rationale:** Enforces data privacy and access control.

**Violation Impact:** Privacy violation; unauthorized data access.

---

### BR-SEC-003: Audit Trail Immutability
**Enforcement:** Domain

**Category:** Invariant  
**Description:** Audit trail entities (ConversationTurns, Episodes, Summaries, Introspections, MetricValues) are immutable and cannot be deleted through normal operations.

**Rationale:** Prevents tampering with historical records.

**Violation Impact:** Lost accountability; regulatory compliance failures.

---

## Conclusion
These business rules form the **invariant core** of the Aiden Memory Agent Chat system. They are:
- **Implementation-independent:** Valid regardless of database, framework, or deployment
- **Testable:** Each rule can be validated through unit or integration tests
- **Traceable:** Rule IDs enable cross-referencing in code comments and test descriptions
- **Complete:** Cover all entity interactions and lifecycle events

All implementation code must enforce these rules. Violations should be caught at the earliest possible layer:
- Domain layer: type safety and invariant checks
- Application layer: process orchestration and validation
- Infrastructure layer: persistence constraints
- Presentation layer: input validation

**When in doubt, refer to these rules as the source of truth.**
