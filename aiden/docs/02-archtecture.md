# Phase 5 Architecture

## Event-Driven Core Principle

**Philosophy:** All state mutations are event-sourced. The API is a thin 
event-producing layer; workers are event-consuming transformation engines.

### Pattern: Async Mutation with Events

1. Client POSTs to `/api/v1/foos`
2. API validates request, returns `202 Accepted` with `operationId`
3. API publishes `FooCreationRequested` event
4. Worker consumes event, performs creation, publishes `FooCreated` event
5. Client polls `/api/v1/operations/{operationId}` or receives webhook

**API Impact:**
- All creation endpoints return 202, not 201
- All endpoints include `/operations/{id}` status polling
- Event subscription API for webhooks
- Idempotency keys required for mutations

### Pattern: Worker Units of Work

**Unit of Work:** Atomic transformation with clear input/output contract

**Example:** `CreateFooWorker`
- Input: `FooCreationRequested` event
- Transformation: Validate + Insert + Publish
- Output: `FooCreated` or `FooCreationFailed` event

**Worker API Exposure:**
- Every worker exposed as `/api/v1/workers/{workerType}/jobs`
- Submit job, poll status, retrieve result
- Enables testing, debugging, manual retry

### Pattern: Template Instantiation (Denormalized Data + Audit Reference)

**Philosophy:** Templates serve creation-time utility, not runtime dependency. Once instantiated, instances are operationally independent.

**Instantiation Flow:**
1. User selects ServiceTemplate or ToolTemplate
2. System copies all structural fields to new Service/Tool instance
3. System sets instance.templateId = template.uuid (immutable audit field)
4. Instance and template become independent entities
5. Template can be modified/archived (or even deleted) without affecting instances

**Reference Semantics:**
- `serviceTemplateId` / `toolTemplateId` are soft references (provenance only)
- No referential integrity constraints enforced at database level
- UI handles archived template references gracefully: "Created from: [Template Name] (archived)"
- Instances contain complete structure and operate identically whether template exists or not

**Deletion Behavior:**
- Template archival: Always allowed, never blocked by instance references
- Instance deletion: Follows normal dependency rules (blocked if other entities reference it)

**API Impact:**
- DELETE /service-templates/{id} returns 202 Accepted (no 409 dependency checking)
- DELETE /tool-templates/{id} returns 202 Accepted (no 409 dependency checking)
- GET /services/{id} may show archived template in provenance ("template archived" tag)
- GET /tools/{id} may show archived template in provenance ("template archived" tag)

### Pattern: Runtime Dependency Validation

**Philosophy:**
Shared resources may become unavailable during Process execution through internal actions (owner unshares) or external forces (IT revokes Secret, API becomes unavailable). System treats all failures identically.

**Dependency Failure Sources:**
- **Internal:** Owner unshares Tool (shared=true → false)
- **External:** Owner's Secret revoked by IT department
- **External:** External API changes/becomes unavailable
- **External:** Credentials expire or are rotated

**Design Principle:**
No attempt to distinguish "legitimate" vs "illegitimate" breaks. Owner controls resources, system fails gracefully with clear diagnostics.

**Validation Flow:**
1. **At Process creation/update:** Validate Tool access (BR-PROCESS-011)
2. **At execution time:** Re-validate dependencies (BR-EXEC-003)
3. **On failure:** Log detailed reason and affected resources
4. **To user:** Surface actionable error with suggested remediation

**Failure Response Pattern:**
```json
{
  "error": "ProcessExecutionFailed",
  "step": 2,
  "stepName": "Fetch Weather",
  "reason": "Tool 'WeatherAPI' owned by @alice is no longer shared",
  "suggestedAction": "Contact @alice to restore access or replace with accessible tool",
  "timestamp": "2025-12-04T10:35:00Z"
}
```

**Logging Requirements:**
- Event type: `process.execution_failed.tool_inaccessible`
- Capture: Tool ID, owner ID, failure reason, affected resources
- Correlation: Link to conversation, process, step for diagnostics

**UI Requirements:**
- Proactive health check: GET /processes/{id}/health
- Status indicators: ✅ Healthy / ⚠️ Warning / ❌ Error
- Clear failure messages with owner contact information
- Suggested actions for remediation

**Cross-References:**
- BR-SHARE-009: Unsharing effects (warn-and-allow model)
- BR-EXEC-003: Runtime validation rules

## Error Handling Architecture

### Error Categories

1. **Client Errors (4xx)** - Request problem, client must change request
2. **Server Errors (5xx)** - System problem, client may retry
3. **Business Rule Violations** - Special case of 4xx with rule reference

### Standard Error Response
```yaml
error:
  code: ERROR_CODE          # Machine-readable
  message: "Description"     # Human-readable
  correlationId: "uuid"      # For support/debugging
  timestamp: "ISO8601"       # When error occurred
  details:                   # Additional context
    field: "fieldName"
    rule: "BR-XXX-NNN"       # When applicable
    retryable: boolean       # Can client retry?
    retryAfter: number       # Seconds to wait (if retryable)
```

### Retryability Matrix

| Error Code | Retryable | Strategy |
|------------|-----------|----------|
| 400 | No | Fix request |
| 404 | No | Resource doesn't exist |
| 409 | Maybe | If transient conflict |
| 422 | No | Business rule violation |
| 429 | Yes | Respect Retry-After |
| 500 | Yes | Exponential backoff |
| 503 | Yes | Service temporarily unavailable |

## Observability Architecture

### Request Tracing

**Every request includes:**
- `X-Request-ID` (client-provided or generated)
- `X-Correlation-ID` (for distributed traces)
- Propagated through events and worker jobs

**Every response includes:**
- Same correlation IDs echoed back
- `X-Response-Time` (milliseconds)

### Health Checks

**Endpoint:** `/health`
- Returns 200 if system operational
- Includes dependent service status
- Does NOT count against rate limits

**Endpoint:** `/health/live`
- Kubernetes liveness probe
- Returns 200 if process running

**Endpoint:** `/health/ready`
- Kubernetes readiness probe  
- Returns 200 if ready to serve traffic

### Metrics Exposure

**Endpoint:** `/metrics`
- Prometheus format
- Request counts, latencies, error rates
- Business metrics (entities created, jobs processed)
- Worker queue depths

---

### Metrics Collection & Exposure Pipeline

**Internal Collection (Application → MetricValues):**
- Workers record MetricValues after each job (execution time, token usage, error counts)
- Services record health check results as MetricValues
- API layer records request latencies as MetricValues
- Storage: MetricValues stored in Neo4j for long-term analytics and business intelligence

**External Exposure (MetricValues → Prometheus):**
- Background aggregator process runs every 60 seconds
- Aggregator queries recent MetricValues (last 5 minutes) from Neo4j
- Aggregator computes aggregations per MetricDefinition (sum/avg/min/max/count)
- Aggregator exposes aggregated metrics at `/metrics` in Prometheus format

**Example Flow:**
```
1. Worker completes job → Inserts MetricValue { metricId: 'tool_exec_time', entityId: 'tool-123', value: 250 }
2. Aggregator queries → Finds 20 MetricValues for 'tool_exec_time' in last 5 minutes
3. Aggregator computes → avg=245ms, p95=380ms, p99=520ms
4. Prometheus scrapes /metrics → Gets tool_exec_time_avg{tool_id="tool-123"} 245
```

**Why Separate Storage:**
- MetricValues in Neo4j enable complex business queries (e.g., "Which Tools have highest failure rate per Conversation?")
- Prometheus optimized for real-time monitoring dashboards, not historical deep analysis
- Aggregator provides bridge: detailed storage + operational monitoring

---

## Platform Capabilities

### Authentication

**Mechanism:** Bearer token (JWT)
```
Authorization: Bearer <token>
```

**Token Claims:**
- `sub`: User ID
- `iat`, `exp`: Issued/Expiry timestamps
- `scope`: Permissions

**Anonymous Access:** None - all endpoints require auth

### Secret Ownership & Access Control (BR-SECRET-001, BR-SECRET-002A, BR-SECRET-002B, BR-SEC-001)

- `sub` claim becomes `userId` for all Secret creation/rotation/deletion requests; `userId` is immutable and stored on Secrets.
- All Secret queries and event subscriptions are filtered by `userId`; non-owners receive 404 to avoid leaking existence.
- Tool execution validates `secretId` belongs to the same `userId` as the Tool and the Conversation using it; cross-user credentials are rejected.
- System/background processes operate with impersonation context for a specific `userId`; admin access is explicitly audited.
- Secrets are never exposed in plaintext; responses and events only include metadata and user ownership.

### Visibility & Authorization (Sharing Model)

**Query Pattern (per entity type: ServiceTemplate, ToolTemplate, Service, Tool, Secret):**
- Return items where `(ownerId == auth.userId) OR (shared == true)`.
- Filters: `owned=true` → `ownerId == auth.userId`; `shared=true` → `shared == true`.
- List responses include `ownerId`, `shared`, and owner attribution string for UX (“Alice’s Tool”).

**Permission Matrix**
| Action | Owner | Non-owner (shared=true) | Non-owner (shared=false) |
|--------|-------|-------------------------|--------------------------|
| View metadata | ✅ | ✅ | ❌ (404) |
| Execute/Use | ✅ | ✅ | ❌ (404/403 per API) |
| Modify properties | ✅ | ❌ (403) | ❌ (403) |
| Delete | ✅ | ❌ (403) | ❌ (403) |
| Toggle shared | ✅ | ❌ (403) | ❌ (403) |
| Reference in own resource | ✅ | Allowed if `shared=true` | ❌ (422/404) |

**Cross-User Reference/Execution (BR-SHARE-005/007/006):**
- Tool.ownerId != Service.ownerId → require `Service.shared=true`; else 422.
- Service.ownerId must equal Secret.ownerId; Secrets never cross users (reject 403/422).
- Executor Conversation.userId != Tool.ownerId → require `Tool.shared=true` or reject.
- Dependencies prevent unsharing/deletion if referenced by other users (409).

**Resource Cost Attribution (BR-SHARE-008):**
- Shared execution bills the resource owner (e.g., executing another user’s Tool consumes their tokens/credentials).
- Audit trail records executor + owner for every cross-user use.

## Resource Management

**Philosophy:** No artificial limits. System runs at full speed. 
Real resource constraints (connections, memory, disk) surface naturally 
as errors. Monitor actual utilization, fix actual bottlenecks.

### Failure Modes
- Database connection exhaustion → 503 Service Unavailable
- Out of memory → 500 Internal Server Error  
- Disk full → 500 Internal Server Error
- Network timeout → 504 Gateway Timeout

**Response:** Fix the actual problem (scale hardware, optimize code), 
don't artificially slow down the working system.

### Pagination

**Query Parameters:**
```
?page=1           # Page number (1-indexed)
?limit=20         # Items per page (max 100)
?sortBy=createdAt # Sort field
?sortOrder=desc   # asc or desc
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 237,
    "totalPages": 12,
    "hasNext": true,
    "hasPrev": false
  }
}
```

### Idempotency

**Header:** `Idempotency-Key: <client-generated-uuid>`

**Behavior:**
- Required for all POST/PUT/DELETE
- Key stored with operation for 24 hours
- Duplicate requests return original response (200, not 202)
- Enables safe retries

## Worker Architecture

### Worker Responsibilities

1. **Consume events** from message queue
2. **Apply transformation** per unit of work
3. **Publish result events**
4. **Update job status** for polling

### Worker API Pattern

**Submit Job:** `POST /api/v1/workers/{workerType}/jobs`
```json
{
  "input": {...},
  "priority": "normal",
  "idempotencyKey": "uuid"
}
```

**Response:** 202 Accepted
```json
{
  "jobId": "uuid",
  "status": "queued",
  "statusUrl": "/api/v1/workers/{workerType}/jobs/{jobId}"
}
```

**Poll Status:** `GET /api/v1/workers/{workerType}/jobs/{jobId}`
```json
{
  "jobId": "uuid",
  "status": "completed",  // queued|processing|completed|failed
  "progress": 100,
  "result": {...},
  "error": null,
  "startedAt": "ISO8601",
  "completedAt": "ISO8601"
}
```

### Failure Handling

- **Transient failures:** Retry with exponential backoff (max 3 attempts)
- **Permanent failures:** Move to dead letter queue
- **Manual retry:** Via API endpoint

---

## ProcessStep Execution Engine

### Execution Model Overview

ProcessSteps are the atomic units of work in the system. Each ProcessStep corresponds to exactly one Worker job that executes a Tool against a Service.

**Synchronous vs Asynchronous:**
- **Mutating operations** (Process execution creating Turns, Summaries, etc.) → Asynchronous via job queues
- **Non-mutating queries** (UI data fetching, health checks) → Synchronous for low latency
- This split optimizes for responsiveness while ensuring consistency

---

### Job Lifecycle

```
1. ProcessStep Scheduling
   - Process execution engine evaluates step dependencies (dependsOn)
   - Steps with satisfied dependencies → Job created and enqueued
   - Parallel steps → Multiple jobs enqueued simultaneously

2. Job Enqueueing
   - Job placed on queue matching Tool Service type (graph_query queue, llm_call queue, etc.)
   - Job includes: stepId, toolId, bound inputs (after interpolation), timeout, requiredness

3. Worker Assignment
   - Idle Worker of matching type pulls job from queue
   - Worker status: idle → busy
   - Worker records currentJobId

4. Tool Execution
   - Worker loads Tool configuration (connectionParams, operation, schemas)
   - Worker validates inputs against Tool inputSchema
   - Worker invokes Service using Tool-specific operation (Cypher query, HTTP request, LLM prompt, etc.)
   - Worker captures raw result

5. Output Processing
   - Worker validates result against Tool outputSchema
   - Worker extracts output.variable value
   - Worker records MetricValues (execution time, token usage, etc.)

6. Result Publishing
   - Worker publishes ProcessStepCompleted event with output
   - If step failed and output.required=true → ProcessFailed event
   - If step failed and output.required=false → ProcessStepSkipped event with null output
   - Worker status: busy → idle, clears currentJobId

7. Process Continuation
   - Process orchestrator receives event
   - Downstream steps with newly-satisfied dependencies → Enqueue more jobs
   - If all steps complete → Process publishes final result
```

---

### Worker Pool Management

**Pool Sizing:**
- One worker pool per Service type (neo4j_graph workers, anthropic_llm workers, mcp_server workers)
- Pool sizes configured independently based on expected load
- Horizontal scaling: increase pool size by deploying more worker instances

**Job Distribution:**
- Round-robin or priority-based assignment within pool
- Failed jobs retry with exponential backoff (max 3 attempts)
- Dead letter queue for permanently failed jobs

**Worker Health:**
- Workers send heartbeats every 30 seconds
- Workers with stale heartbeats (>90 seconds) marked offline
- Jobs assigned to offline workers automatically reassigned

---

### Timeout Handling

ProcessStep `execution.timeout` enforced at Worker level:
- Worker sets timeout timer on job start
- If timeout expires before Tool completes:
  - Worker terminates Tool execution (gracefully if possible)
  - Worker publishes ProcessStepTimeout event
  - Handling per step `output.required` flag (fail Process or continue with null)

---

### Conditional Execution

ProcessStep `execution.condition` evaluated before enqueueing:
- Process engine evaluates condition expression against current context
- If condition=false → Step skipped, no job created
- If condition=true → Job enqueued normally

---

### Manual Interaction Mode

ProcessStep with `execution.interactionMode='manual'`:
- Worker pauses after enqueueing
- System publishes HumanInputRequired event with context
- UI prompts user for input
- User provides input → Worker resumes with user input as step output
- Timeout applies to human response time

---

### Error Propagation

Worker errors include full context for debugging:
```json
{
  "processId": "proc-123",
  "stepId": "step-5",
  "toolId": "tool-anthropic-claude",
  "serviceId": "service-anthropic",
  "errorType": "ServiceUnavailable",
  "errorMessage": "Connection timeout after 30s",
  "retryCount": 2,
  "timestamp": "2025-01-15T10:23:45Z"
}
```

This enables precise failure diagnosis and supports exponential backoff retry logic.

---

## Context Assembly With Entities

### Flow Overview
```
Conversation Turn
   |
   v
Episode (captured in Graphiti, group_id = userId)
   |
   +--> Entity Extraction (Graphiti) ---> Dedup Queue ---> Unified Entity UUID
   |                                   (merges user + AI sources)
   |
   +--> Summary Creation (on token threshold) ---> Summary Episode (group_id = userId)
   |                                            |
   |                                            +--> Compression Counter++
   |                                            |
   |                                            +--> Introspection Trigger Check
   |                                                 (if compressionCount >= threshold)
   |                                                          |
   |                                                          v
   |                                            Introspection Process (async, non-blocking)
   |                                                 |- Semantic search: user's Episodes, Summaries, Entities
   |                                                 |- Semantic search: user's Introspection history (carousel + archives)
   |                                                 |- Agent reflects, reorganizes carousel knowledge
   |                                                 |- Creates Introspection Episode (group_id = userId)
   |                                                 |- Replaces carousel position (circular, preserves archives)
   |                                                 |
   |                                                 v
   |                                            Agent Persona Development (per user)
   |
WorkingMemory Builder (per conversation turn)
   |- immediateEpisodes (latest Episode UUIDs from active path)
   |- summaries (cached Summary IDs)
   |- activeEntities (EntityReference objects)
   |- introspectionContext (current carousel Introspection Episodes, user-scoped)
   |
   v
Context Package → Prompt Construction
   |- Conversation history (immediateEpisodes + summaries)
   |- Domain knowledge (activeEntities with facets/relationships)
   |- Agent persona (introspectionContext - learned skills, patterns, understanding)
```

**Context Assembly Components:**

- **Episode Creation:** Every Turn captured in Graphiti with `group_id = userId` for user-scoped semantic search
- **Entity Extraction:** Graphiti extracts entities from Episodes; deduplication merges user-created and AI-extracted entities into canonical UUIDs
- **Summary Creation:** When WorkingMemory exceeds token threshold, compression creates Summary Episode; increments compression counter
- **Introspection Trigger:** After N compressions (default: 5), triggers async introspection process
- **Introspection Process:** Agent searches user's Episodes, Summaries, Entities, and Introspection history; reflects and creates new Introspection Episode; updates carousel (circular replacement, preserves archives)
- **WorkingMemory Assembly:** Combines conversation history (immediateEpisodes + summaries), domain knowledge (activeEntities), and agent persona (introspectionContext)
- **Prompt Construction:** Context package includes all three components: what was said (Episodes/Summaries), what it's about (Entities), and who the agent is (Introspections)

**User-Scoped Knowledge (group_id = userId):**
- Episodes, Summaries, Entities, and Introspections all scoped to userId
- Agent learns across user's conversations (not isolated per conversation)
- Persona development persists and evolves over time
- Each user trains their own agent through interaction

**Async Introspection (Non-Blocking):**
- Introspection happens in background after compression events
- User conversation continues without waiting
- Agent persona gradually improves through reflection
- Carousel maintains bounded working set (10 positions) while archiving history

---

## Graphiti Integration Layer

### Integration Boundary

Graphiti manages Episodes, Entities, entity extraction, semantic search, and temporal facts. The application treats Graphiti as an external semantic knowledge store with the following integration points:

**Application → Graphiti (Write Operations):**
1. **Episode Creation:** When ConversationTurn is created, application sends Episode to Graphiti via API
2. **Summary Storage:** When Summary is created, application sends summary Episode to Graphiti
3. **Introspection Recording:** When Introspection is created, application sends reflection Episode to Graphiti

**Graphiti → Application (Read Operations):**
1. **Semantic Search:** Application queries Graphiti for relevant Episodes by semantic similarity
2. **Entity Retrieval:** Application fetches Entity details by UUID
3. **Relationship Traversal:** Application explores entity neighborhoods via Graphiti graph queries

**Graphiti → Application (Events):**
1. **Entity Extraction Complete:** Graphiti publishes event when Episode processing yields new/updated Entities
2. **Deduplication Candidate:** Graphiti publishes event when entity similarity exceeds threshold

---

### Episode Binding Pattern

**Turn/Alternative Creation (Synchronous + Immediate UI response)**
1. API validates request and creates ConversationTurn + Alternative with `episodeId = null`
2. API persists turn graph and returns `202 Accepted` with `operationId`
3. API publishes `TurnCreated` (or equivalent) event for downstream workers
4. User immediately sees their message/response because UI renders from persisted Turn content, not Graphiti

**Episode Backfill (Asynchronous)**
1. EpisodeIngestionWorker consumes `TurnCreated` event
2. Worker creates Graphiti Episode named `Turn:{alternativeId}` (contains full content, conversation/group metadata)
3. Worker updates `Alternative.episodeId` once Graphiti confirms write
4. Downstream processes (entity extraction, summaries, search) react when `episodeId` transitions from `null → uuid`

**Failure Handling:**
- Worker retries transient Graphiti errors; after max attempts it emits failure event for ops dashboards
- User operations remain successful; only knowledge-graph enrichment is delayed until Episode creation succeeds
- Observability dashboards highlight Alternatives still awaiting `episodeId` so support can intervene if backlog forms

---

### Content Storage Pattern

**Architectural Decision: Permanent Dual Storage**

```
┌─────────────────────┐
│ ConversationTurn    │
│ - content: string   │ ← UI always reads from here (display layer)
│ - episodeUUID: ref  │ ← Backfilled by polling worker
└─────────────────────┘
         │
         │ Fire-and-forget
         ↓
┌─────────────────────┐
│ Graphiti Episode    │
│ - name: "Turn:uuid" │ ← Embeds Turn UUID for matching
│ - content: string   │ ← Semantic search & knowledge layer
└─────────────────────┘
```

**Design Rationale**
1. **Turn.content = Display Source of Truth** — UI renders directly from Turns; no Graphiti dependency for display.
2. **Episode.content = Knowledge Index** — Graphiti operates on Episode content for semantic search, entity extraction, enrichment.
3. **No Content Deletion** — Turn.content and Episode.content are permanent; no archival dependency, minimal complexity.

**Intentional Duplication:** Same text stored twice but serves different layers; ensures separation of concerns rather than waste.

**Polling Worker Matching:** Worker correlates Episodes to Turns by searching for `name === "Turn:{turn.uuid}"`, providing deterministic linkage.

---

### Entity Extraction Async Flow

**Trigger:** Episode creation in Graphiti automatically triggers entity extraction

**Flow:**
```
1. Graphiti processes Episode content (NLP, LLM extraction)
2. Graphiti creates/updates Entities with entity_type, summary, facts
3. Graphiti links Episode → Entity via entity_edges
4. Graphiti publishes EntityExtractionComplete event

5. Application worker consumes event
6. Application fetches new/updated Entities by UUID
7. Application updates Conversation.activeEntities if relevant
8. Application enqueues deduplication check if similarity threshold met
```

**Non-Blocking:** Entity extraction happens in background; user conversation continues immediately

---

### Semantic Search Integration

**Use Cases:**
- WorkingMemory assembly: Find relevant past Episodes
- Introspection: Agent searches all introspection history
- Entity enrichment: Find all Episodes mentioning entity

**API Call:**
```typescript
const results = await graphiti.semanticSearch({
  query: "quantum entanglement explanation",
  groupId: conversationId,  // scope to conversation
  limit: 10,
  threshold: 0.7  // similarity threshold
});

// Returns: Array<{ episodeId, similarity, content }>
```

**Caching:** Application may cache search results per conversation for session duration; invalidate on new Episodes

---

### Retry & Resilience

**Graphiti Unavailable:**
- Critical path (Episode creation) → Fail request, return 503
- Background path (entity extraction events) → Exponential backoff retry (max 3 attempts, then dead letter queue)

**Partial Failures:**
- Episode created but extraction failed → Retry extraction via admin API
- Entity created but deduplication skipped → Deduplication runs on next entity extraction

**Monitoring:**
- Track Graphiti API latency via MetricValues
- Alert on sustained high latency or error rates
- Health check includes Graphiti connectivity

---

### Data Consistency Guarantees

**Strong Consistency (Synchronous):**
- ConversationTurn + Alternative persistence (content, DAG edges) occurs in the request transaction
- Operation events (TurnCreated, ProcessStepRequested, etc.) are emitted atomically with the write

**Eventual Consistency (Asynchronous):**
- Alternative.episodeId remains `null` until the ingestion worker finishes creating the Graphiti Episode
- Episode → Entity extraction: Entities appear in activeEntities after extraction completes
- Entity → Deduplication: Merged entities eventually replace candidates
- Enrichment → Entity updates: Enriched summaries/facets eventually available

**Implications:**
- Users may see Turns before extracted entities appear (acceptable)
- Entity references stable after deduplication (UUIDs updated atomically)

---

### Entity Deduplication

- Graphiti similarity matching (name + summary vectors) feeds a Dedup Worker that merges overlapping entities.
- Dedup workflow copies all `sources`, `fact_ids`, and `entity_edge_ids` into the surviving entity, preferring user UUIDs when conflicts exist.
- Conversation and WorkingMemory references always point at the merged UUID; historical provenance stays intact for auditing.

### Entity Enrichment Background Job

- When an entity accumulates edge density (Episode mentions + relationships) beyond the configured threshold, an enrichment worker runs.
- Worker performs semantic search across related Episodes and Summaries, assembles relationship graphs, and feeds the result into an LLM synthesis prompt.
- Output updates entity `enrichment` payload and inferred facets while keeping `sources` append-only, so WorkingMemory inclusion flags can selectively pull summaries/facets/relationships into prompts.
- Enrichment also recalculates `relevanceScore` hints that help prioritize entities inside `activeEntities`.

---

## Context Compression Strategy

### Compression Triggers

**Automatic Trigger:**
- WorkingMemory token count exceeds configured threshold (default: 80% of Process tokenBudget)
- Triggered per conversation when assembling context for new Turn
- Compression runs asynchronously; current Turn may use uncompressed context

**Manual Trigger:**
- User requests "Summarize conversation so far"
- Admin initiates compression for storage optimization

---

### Compression Algorithm

**Sequential Compression (Default):**
```
1. Identify compression window
   - Start: Oldest Episode in WorkingMemory not yet summarized
   - End: Newest Episode at least N turns old (default: N=5, preserve recent detail)
   - Window size: 5-10 Episodes (configurable)

2. Invoke summarization Tool
   - Tool: Configured LLM with prompt template for compression
   - Input: Episode contents from window
   - Output: Compressed summary text (target: 30% of original tokens)

3. Create Summary entity
   - Summary content stored as new Episode in Graphiti (source='summary')
   - Summary references source Episode UUIDs
   - CompressionLevel = max(source Episodes) + 1

4. Update WorkingMemory
   - Remove compressed Episodes from immediatePath
   - Add Summary to summaries array
   - Recompute totalTokens

5. Increment compression counter
   - CompressionCounter.compressionCount++
   - Check if introspection threshold reached
```

**Selective Compression (Future):**
- Prioritize Episodes with low relevance scores
- Preserve Episodes with high user engagement (starred, referenced)
- Multi-level compression: compress summaries into higher-level summaries

---

### Compression Level Hierarchy

```
Level 0: Original Episodes (Turn content)
Level 1: First-level Summary (compresses 5-10 Episodes)
Level 2: Second-level Summary (compresses 5-10 Level 1 Summaries)
...
Level N: Nth-level Summary
```

**Invariant:** Summary.compressionLevel = max(sourceEpisode.compressionLevel) + 1

**Limit:** Max compression level = 5 (prevents over-compression losing detail)

---

### Token Budget Management

**Before Compression:**
```
WorkingMemory.totalTokens = 
  sum(immediatePath Episodes) + sum(summaries) + sum(activeEntities)
```

**Compression Decision:**
```typescript
if (totalTokens > process.tokenBudget * 0.8) {
  const compressionJob = {
    conversationId,
    windowStart: oldestUncompressedEpisodeId,
    windowEnd: episodeId_N_turnsAgo,
    targetCompressionRatio: 0.3
  };
  enqueueCompressionJob(compressionJob);
}
```

**After Compression:**
- Total tokens reduced by ~50-70% for compressed window
- Recent Episodes remain uncompressed for detail preservation

---

### Compression Quality Metrics

Tracked via MetricValues:
- `compression_ratio`: Original tokens / Compressed tokens
- `compression_time_ms`: Time to compress window
- `information_loss_score`: Semantic similarity between original and summary (0-1)

**Quality Thresholds:**
- If compression_ratio < 0.2 → Summary too aggressive, increase target ratio
- If information_loss_score < 0.7 → Summary too lossy, adjust prompt or window size

---

### Compression & Introspection Coordination

```typescript
// After each compression
compressionCounter.compressionCount++;

if (compressionCounter.compressionCount - compressionCounter.lastIntrospectionAt 
    >= introspectionCompressionThreshold) {
  
  // Trigger introspection job
  enqueueIntrospectionJob({
    conversationId,
    recentCompressions: getLastNCompressions(5),
    carouselPosition: nextCarouselPosition
  });
  
  compressionCounter.lastIntrospectionAt = compressionCounter.compressionCount;
}
```

This ensures introspection happens at regular compression intervals, allowing the agent to reflect on evolving conversation context.

---

## Conversation Alternatives Architecture

### Philosophy: User-Controlled Display Path with System Recording

Conversations are **user-navigable graphs** where:
- **User inputs are mutable scripts:** Users revise prompts at any Turn, creating new alternatives in-place.
- **Agent responses are derived alternatives:** Multiple Processes can respond to the same input; regenerations append more alternatives.
- **User controls the active path:** User clicks alternatives in the UI; the system records which alternative is on screen via `isActive`.
- **Context reflects the on-screen path:** WorkingMemory traverses `isActive` alternatives (user selection) from current tip back to root.
- **Cache status is feedback:** System marks agent alternatives as `valid`, `stale`, or `generating`; user decides whether to regenerate.
- **System records, never chooses:** There is no canonical branch—data mirrors whatever the user currently views.

---

### Alternative Tree Structure & UI Concept

```
Turn 1 (User)  [1 of 1]
  alt-1 (active)
  |
  +-- Turn 2 (Agent)  [1 of 2]
      alt-1: Claude response (active, valid)
      alt-2: GPT-4 response (inactive, stale)
      |
      +-- Turn 3 (User)  [2 of 2]
          alt-1: "Tell me more" (inactive)
          alt-2: "Specifically about entanglement?" (active)
          |
          +-- Turn 4a (Agent, parent alt-1)  [1 of 1] ⚠ stale
          +-- Turn 4b (Agent, parent alt-2)  [1 of 1] ✅ valid
```

- Turn cards show `[current of total]` indicator with ← → controls.
- User cycles alternatives; selected alternative becomes `isActive=true`.
- Descendants referencing a different parent alternative dim/flag as stale.

---

### Active Path Cascade Behavior

**Principle:** `isActive` defines a single active path from root to any focused Turn. Selecting an alternative triggers automatic ancestor cascade and descendant cache invalidation while preserving off-path alternatives.

---

#### Three-Phase Cascade Algorithm

**Phase 1: Local Update (Atomic)**
```typescript
function selectAlternative(turnId, alternativeId) {
  const turn = getTurn(turnId);

  turn.alternatives.forEach(alt => {
    alt.isActive = (alt.id === alternativeId);
  });

  const selectedAlt = turn.alternatives.find(a => a.id === alternativeId);

  cascadeAncestors(turn, selectedAlt);
  invalidateDescendants(turn);
  rebuildWorkingMemory(conversationId, turnId, alternativeId);
}
```

**Phase 2: Ancestor Cascade (Recursive to Root)**
```typescript
function cascadeAncestors(turn, selectedAlt) {
  let currentTurn = turn;
  let requiredParentAltId = selectedAlt.inputContext.parentAlternativeId;

  while (currentTurn.parentTurnId && requiredParentAltId) {
    const parentTurn = getTurn(currentTurn.parentTurnId);
    parentTurn.alternatives.forEach(alt => {
      alt.isActive = (alt.id === requiredParentAltId);
    });

    const activeParentAlt = parentTurn.alternatives.find(
      a => a.id === requiredParentAltId
    );

    requiredParentAltId = activeParentAlt.inputContext.parentAlternativeId;
    currentTurn = parentTurn;
  }
}
```

**Phase 3: Descendant Invalidation (Recursive to Leaves)**
```typescript
function invalidateDescendants(turn) {
  const activeAlt = turn.alternatives.find(a => a.isActive);
  const children = getChildTurns(turn.id);

  children.forEach(child => {
    child.alternatives.forEach(childAlt => {
      if (childAlt.inputContext.parentAlternativeId === activeAlt.id) {
        childAlt.cacheStatus = 'valid';
      } else {
        childAlt.cacheStatus = 'stale';
      }
    });

    invalidateDescendants(child);
  });
}
```

---

#### Example Cascade

User switches Turn 2 to alt-2:
- **Local:** Turn 2 alt-2 active, alt-1 inactive
- **Ancestors:** Turn 1 already aligned (remains active)
- **Descendants:** Turn 3/4 marked stale because they depended on Turn 2 alt-1
- UI displays stale indicators and regeneration buttons; user decides whether to regenerate

---

#### WorkingMemory Rebuild

After cascade, WorkingMemory rebuild walks `isActive` alternatives from selected Turn to root, guaranteeing coherent path:
```typescript
while (turn) {
  const alt = turn.alternatives.find(a => a.id === altId);
  path.unshift({ turnId: turn.id, alternativeId: alt.id, episodeId: alt.episodeId });

  if (!turn.parentTurnId) break;
  turn = getTurn(turn.parentTurnId);
  altId = alt.inputContext.parentAlternativeId;
}
```

---

#### UI Navigation Patterns

- **Cycle alternatives:** `selectAlternative` called with next/prev alternative → full cascade
- **Focus on Turn:** Selecting Turn triggers cascade even if active alternative unchanged (ensures ancestors correct)
- **Reactivate stale alternative:** Clicking “Use this response” on stale alternative triggers cascade from that Turn, re-validating path

---

#### Edge Cases

- **Root Turn:** Ancestor cascade stops immediately; only local update + descendant invalidation run
- **Leaf Turn:** No descendants to invalidate
- **Deep selection:** Complexity O(depth + descendants); acceptable (<20 depth typical)

---

### Alternative Types and Creation

#### User Alternatives (Prompt Revisions)
- Triggered by Edit action on a user Turn.
- Creates new alternative referencing new Episode; immediately set to `isActive=true`.
- Prior alternatives remain for audit; user can switch back anytime.
- Descendant agent alternatives recompute cache status: compare their `inputContext.parentAlternativeId` to new parent active alternative.

#### Agent Alternatives (Process Variations & Regenerations)
- Triggered when user regenerates, tries another Process, or continues from another parent alternative.
- Each records `processId`, `createdAt`, and `inputContext.parentAlternativeId`.
- User chooses which agent alternative to display; system records the choice.

---

### Cache Status & Lazy Regeneration

```typescript
function deriveCacheStatus(turn, alternative) {
  if (turn.speaker === 'user') return 'valid';
  if (alternative.episodeId === null) return 'generating';

  if (!turn.parentTurnId) return 'valid';

  const parentTurn = getTurn(turn.parentTurnId);
  const parentActiveId = parentTurn?.alternatives.find(a => a.isActive)?.id;

  return alternative.inputContext.parentAlternativeId === parentActiveId
    ? 'valid'
    : 'stale';
}
```

- `valid`: Response matches upstream selection.
- `stale`: Upstream selection changed since this response was generated.
- `generating`: Process still running.

Regeneration is lazy. Stale alternatives remain until the user explicitly regenerates or switches back. This keeps compute focused on the active tip while preserving history.

---

### WorkingMemory Assembly from User Selection

```typescript
function assembleWorkingMemory(conversationId, currentTurnId, currentAlternativeId) {
  const path = [];
  let turn = loadTurn(currentTurnId);
  let altId = currentAlternativeId;

  while (turn) {
    const alt = turn.alternatives.find(a => a.id === altId && a.isActive);
    path.unshift({ turnId: turn.id, alternativeId: alt.id, episodeId: alt.episodeId });

    if (!turn.parentTurnId) break;  // reached root

    turn = loadTurn(turn.parentTurnId);                 // structural parent
    altId = alt.inputContext.parentAlternativeId;       // which alternative in that Turn
  }

  return buildWorkingMemory(conversationId, path.slice(-10));
}
```

- Traversal respects the user’s on-screen selections only.
- WorkingMemory rebuilds whenever the user toggles `isActive` or adds new Turns, guaranteeing the agent sees the same path.

---

### API Patterns

- **GET `/api/v1/conversations/{id}/tree`** – Returns Turns plus full `alternatives[]`, `isActive`, `inputContext`, and derived cache statuses.
- **POST `/api/v1/conversations/{id}/turns/{turnId}/alternatives`** – Creates new alternative (user edit or agent regeneration). Agent executions respond with `202 Accepted` and status polling.
- **PUT `/api/v1/conversations/{id}/turns/{turnId}/alternatives/{altId}/activate`** – Records UI selection by toggling `isActive` and returns affected child Turns for cache indicator updates.
- **POST `/api/v1/conversations/{id}/turns`** – Continues conversation from explicit `{parentTurnId, parentAlternativeId}` context; optional flag auto-regenerates stale parent first.

---

### UI Control Model

```typescript
function onAlternativeClick(turnId, direction) {
  const turn = getTurn(turnId);
  const current = turn.alternatives.findIndex(a => a.isActive);
  const next = direction === 'next'
    ? (current + 1) % turn.alternatives.length
    : (current - 1 + turn.alternatives.length) % turn.alternatives.length;

  turn.alternatives[current].isActive = false;
  turn.alternatives[next].isActive = true;

  recomputeDescendantCacheStatus(turnId);
  rebuildWorkingMemory();
}
```

- User clicks `[← | →]` or dropdown entry; system records new `isActive`.
- Stale descendants show ⚠, valid show ✅, generating show ⏳.
- Regenerate buttons create new alternatives without deleting old ones.

---

### Turn Display Example

```
Turn 3 (User)   [2 of 3]   ← →
"Explain quantum entanglement, focus on measurement"

Turn 4A (Agent, Claude)   [1 of 1]   ⚠ Stale
  Response generated from Turn3 Alt 1
  [Regenerate for current input]  [Show response context]

Turn 4B (Agent, GPT-4)    [2 of 2]   ✅ Valid
  Response generated from Turn3 Alt 2 (what’s on screen)
  [Make Active]  [Try Different Process]
```

User flow:
1. User cycles Turn 3 to Alt 2.
2. System toggles `isActive`, dims Turn 4A, and marks stale.
3. User may regenerate Turn 4A or continue via Turn 4B.

---

### Storage & Indexing

- `idx_turn_active_alt` on `(turnId, alternatives.isActive)` for quick active retrieval.
- `idx_alt_parent_ref` on `(parentTurnId, alternatives.inputContext.parentAlternativeId)` for cache propagation.
- Optional partial index on `(conversationId, alternatives.cacheStatus)` to surface stale nodes in UI.

---

### Migration Strategy

1. **Schema:** Ensure `alternatives[]` records `inputContext.parentAlternativeId` for each entry (parent Turn already provided by Turn.parentTurnId); migrate legacy turns to single alternatives.
2. **User Edits:** Ship UI for creating alternatives; persist `isActive` per user selection.
3. **Agent Variants:** Support “Try Different Process” and “Regenerate” flows generating new alternatives asynchronously.
4. **Active Path:** Expose API to toggle `isActive`; recompute cache state + WorkingMemory after each toggle.
5. **Enhancements:** Provide visualization, comparison views, and subtree regeneration utilities once base behavior stabilizes.

---

## Conversation Forking

### Fork Creation Flow

**Trigger:** User selects "Fork conversation from here" on any ConversationTurn

**API Endpoint:** `POST /api/v1/conversations/{conversationId}/turns/{turnId}/fork`

**Request:**
```json
{
  "title": "Exploring quantum interpretations",
  "copyActiveEntities": true,
  "idempotencyKey": "uuid"
}
```

**Response:** 202 Accepted
```json
{
  "operationId": "op-456",
  "statusUrl": "/api/v1/operations/op-456"
}
```

---

### Fork Worker Process

```
1. Load parent Conversation and origin Turn
   - Validate turnId exists in conversationId
   - Validate user has permission to fork

2. Create new Conversation
   - parentConversationId = original conversationId
   - forkOriginTurnId = specified turnId
   - title = provided or "Fork of {parent.title}"
   - userId = same as parent (user owns both)
   - processId = parent.processId (inherit preferred Process)
   - status = 'active'

3. Copy activeEntities (if requested)
   - forked.activeEntities = parent.activeEntities.slice()
   - Entities remain shared (same UUIDs); forks track independently

4. Initialize WorkingMemory
   - Create empty WorkingMemory for forked conversation
   - No Episodes copied; user continues fresh from fork point

5. Create initial Turn (optional)
   - If origin Turn is user Turn → No initial Turn needed
   - If origin Turn is agent Turn → Create reference Turn linking to parent's Episode
     (so forked conversation has context of what it's responding to)

6. Publish ForkCompleted event
   - Includes new conversationId
   - Client navigates to forked conversation
```

---

### Fork Semantics

**What's Copied:**
- activeEntities array (if copyActiveEntities=true)
- User ownership
- Process preference

**What's NOT Copied:**
- ConversationTurns (starts empty or with reference Turn)
- WorkingMemory Episodes (builds fresh from fork point)
- Summaries (user continues without compression history)

**Rationale:**
- Fork lets user explore "what if" scenarios from a specific point
- Shared entities enable consistent context
- Independent Turn history allows divergent conversation paths

---

### UI Fork Indicator

```
Conversation Header:
  ↳ Forked from "Original Conversation" at Turn 12

Turn 1 (Reference) [Read-only]
  "User asked: Explain quantum entanglement" [View in original →]
```

Reference Turn is read-only and links back to parent conversation for full context.

---

### Parent-Fork Relationships

**Navigation:**
- Parent conversation shows "Forked into: <title>" badge
- Forked conversation shows "Forked from: <parent>" with link

**Entity Sync:**
- Entities remain shared across parent and forks
- User-created entities in fork appear in parent's entity search
- Deduplication merges entities across conversation boundaries

**No Automatic Sync:**
- Turns are independent after fork
- Changes to parent's activeEntities don't affect fork
- User may manually copy entities between conversations

---

## Process Ownership: UI Hint vs Execution Truth

### Dual processId Purposes

```typescript
Conversation {
  processId: string | null  // mutable UI hint
}

Alternative {
  processId: string | null  // immutable execution record
}
```

- **Conversation.processId:** remembers the user’s most recent Process selection to prefill the UI dropdown.
- **Alternative.processId:** permanently records which Process actually executed for that alternative.

---

### Conversation.processId — Persistent UI Hint

**Use case:** Provide sensible default when user clicks “Next agent turn.”

```typescript
function createAgentTurn(convId, selectedProcessId) {
  // 1. Create alternative
  const alt = new Alternative({ processId: selectedProcessId, ... });

  // 2. Update hint (idempotent)
  const conversation = getConversation(convId);
  conversation.processId = selectedProcessId;

  // 3. Execute using the alternative’s processId
  executeProcess(alt.processId, ...);
}
```

- Mutable and idempotent.
- May be null for new conversations until the first agent turn.
- Not a source of truth for execution—purely convenience.

---

### Alternative.processId — Immutable Execution Record

**Use case:** Audit, replay, regenerate, analyze.

```json
Turn 4 alternatives:
[
  { "id": "alt-1", "processId": "claude-sonnet", "episodeId": "ep-101" },
  { "id": "alt-2", "processId": "gpt-4-turbo", "episodeId": "ep-102" }
]
```

- Set when alternative is created and never changes.
- Regeneration uses this value to reproduce the same agent behavior.
- Analytics / observability derive counts per Process from these records.

---

### Update Flow Diagram

```
User selects Process (UI default = conversation.processId)
        │
        ▼
Create alternative → alternative.processId = selection (immutable)
        │
        ▼
Update conversation.processId = selection (mutable hint)
        │
        ▼
Execute process(alternative.processId)
```

Execution never reads conversation.processId; it only updates it for convenience.

---

### When Values Differ (Intentional)

```
Timeline:
T1 agent turn → conversation.processId = 'claude'
T2 agent turn → user picks 'gpt-4'
T3 agent turn → user returns to 'claude'

Current:
- conversation.processId = 'claude'
- T1 alternative.processId = 'claude'
- T2 alternative.processId = 'gpt-4'
- T3 alternative.processId = 'claude'
```

At T2 the user experimented with GPT-4. Later, the hint returned to Claude. Alternative-level data still shows what actually ran for T2.

---

### API Patterns

- **GET Conversation:** returns `processId` to populate “Next turn with …” UI.
- **POST /turns (agent):** request includes selected Process; server creates alternative with that ProcessId and updates conversation.processId.
- **POST /turns/{turnId}/alternatives/{altId}/regenerate:** server reads the alternative’s processId and re-runs that Process, leaving conversation.processId untouched.

---

### Migration Notes

- Existing conversations: interpret processId as last-used hint; allow null if unknown.
- Existing alternatives: ensure future schema writes always include processId for agent/system alternatives.
- Execution pipeline: refactor to reference `alternative.processId` exclusively; treat conversation.processId as optional input to UI only.

---
