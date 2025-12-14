# Endpoint Classification: Sync vs Async

## Classification Rules

**Synchronous (200/404/422):** Read operations, non-mutating queries, immediate validation
**Asynchronous (202 Accepted):** Create/Update/Delete operations, Process executions, Worker jobs

---

## Services

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/services` | GET | Sync | 200 | List query |
| `/api/v1/services/{id}` | GET | Sync | 200/404 | Read query |
| `/api/v1/services` | POST | **Async** | 202 | Create mutation |
| `/api/v1/services/{id}` | PUT | **Async** | 202 | Update mutation |
| `/api/v1/services/{id}` | DELETE | **Async** | 202 | Delete mutation |
| `/api/v1/services/{id}/health` | POST | Sync | 200 | Health check (read) |

---

## Secrets

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/secrets` | GET | Sync | 200 | Owner-scoped metadata read (filters by userId) |
| `/api/v1/secrets/{id}` | GET | Sync | 200/404 | Owner-only metadata (non-owner → 404) |
| `/api/v1/secrets` | POST | **Async** | 202 | Create encrypted secret (userId from auth; event published) |
| `/api/v1/secrets/{id}` | PUT | **Async** | 202 | Rotate encrypted value (owner-only; event published) |
| `/api/v1/secrets/{id}` | DELETE | **Async** | 202 | Delete secret (owner-only; event published) |

---

## Tools

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/tools` | GET | Sync | 200 | List query |
| `/api/v1/tools/{id}` | GET | Sync | 200/404 | Read query |
| `/api/v1/tools` | POST | **Async** | 202 | Create mutation |
| `/api/v1/tools/{id}` | PUT | **Async** | 202 | Update mutation |
| `/api/v1/tools/{id}` | DELETE | **Async** | 202 | Delete mutation |
| `/api/v1/tools/{id}/test` | POST | **Async** | 202 | Test execution (worker job) |

---

## Processes

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/processes` | GET | Sync | 200 | List query |
| `/api/v1/processes/{id}` | GET | Sync | 200/404 | Read query |
| `/api/v1/processes` | POST | **Async** | 202 | Create mutation |
| `/api/v1/processes/{id}` | PUT | **Async** | 202 | Update mutation |
| `/api/v1/processes/{id}` | DELETE | **Async** | 202 | Delete mutation |
| `/api/v1/processes/{id}/execute` | POST | **Async** | 202 | Process execution (worker) |

---

## Conversations

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/conversations` | GET | Sync | 200 | List query |
| `/api/v1/conversations/{id}` | GET | Sync | 200/404 | Read query |
| `/api/v1/conversations/{id}/tree` | GET | Sync | 200/404 | Read tree structure |
| `/api/v1/conversations` | POST | **Async** | 202 | Create mutation |
| `/api/v1/conversations/{id}` | PUT | Sync | 200 | Update metadata only (title, processId hint) |
| `/api/v1/conversations/{id}/turns` | POST | **Async** | 202 | Create Turn (Episode creation) |
| `/api/v1/conversations/{id}/turns/{turnId}/fork` | POST | **Async** | 202 | Fork workflow |

---

## Turns & Alternatives

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/conversations/{id}/turns/{turnId}` | GET | Sync | 200/404 | Read query |
| `/api/v1/conversations/{id}/turns/{turnId}/alternatives` | POST | **Async** | 202 | Create alternative (Episode + possible execution) |
| `/api/v1/conversations/{id}/turns/{turnId}/alternatives/{altId}/activate` | PUT | Sync | 200 | UI selection (metadata only, fast) |
| `/api/v1/conversations/{id}/turns/{turnId}/alternatives/{altId}/regenerate` | POST | **Async** | 202 | Regenerate response (Process execution) |

---

## WorkingMemory

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/conversations/{id}/working-memory` | GET | Sync | 200 | Assemble context (read query) |
| `/api/v1/conversations/{id}/working-memory/compress` | POST | **Async** | 202 | Compression job (worker) |

---

## Summaries

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/conversations/{id}/summaries` | GET | Sync | 200 | Read summaries for conversation |
| `/api/v1/conversations/{id}/summaries/{summaryId}` | GET | Sync | 200/404 | Read specific summary |
| `/api/v1/conversations/{id}/summaries` | POST | **Async** | 202 | Create summary (compression worker) |
| `/api/v1/conversations/{id}/summaries/{summaryId}` | PUT | **Async** | 202 | Update summary episode binding |
| `/api/v1/conversations/{id}/summaries/{summaryId}` | DELETE | **Async** | 202 | Delete summary (triggers recompression) |

---

## Introspections

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/introspections` | GET | Sync | 200 | List carousel entries |
| `/api/v1/introspections/{id}` | GET | Sync | 200/404 | Read specific introspection |
| `/api/v1/introspections` | POST | **Async** | 202 | Create introspection (event published) |
| `/api/v1/introspections/{id}` | PUT | **Async** | 202 | Update introspection content |
| `/api/v1/introspections/{id}` | DELETE | **Async** | 202 | Delete introspection entry |

---

## Entities (Graphiti Integration)

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/entities` | GET | Sync | 200 | Search/list query |
| `/api/v1/entities/{uuid}` | GET | Sync | 200/404 | Read query |
| `/api/v1/entities` | POST | **Async** | 202 | Create entity (Graphiti + dedup) |
| `/api/v1/entities/{uuid}` | PUT | **Async** | 202 | Update entity (Graphiti sync) |
| `/api/v1/entities/{uuid}` | DELETE | **Async** | 202 | Delete entity (Graphiti sync) |

---

## Operations (Status Polling)

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/operations/{id}` | GET | Sync | 200/404 | Poll job status (read query) |
| `/api/v1/operations/{id}/cancel` | POST | **Async** | 202 | Cancel job (worker command) |

---

## Workers (Admin/Debug)

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/api/v1/workers` | GET | Sync | 200 | List workers |
| `/api/v1/workers/{type}/jobs` | POST | **Async** | 202 | Submit worker job |
| `/api/v1/workers/{type}/jobs/{id}` | GET | Sync | 200/404 | Poll job status |

---

## Health & Observability

| Endpoint | Method | Type | Status | Rationale |
|----------|--------|------|--------|-----------|
| `/health` | GET | Sync | 200 | Health check |
| `/health/live` | GET | Sync | 200 | Liveness probe |
| `/health/ready` | GET | Sync | 200 | Readiness probe |
| `/metrics` | GET | Sync | 200 | Prometheus metrics |

---

## Summary Statistics

- **Total endpoints:** 60 (matches OpenAPI path/method inventory)
- **Synchronous endpoints:** 29 (read queries, metadata-only updates, health/metrics)
- **Asynchronous endpoints:** 31 (mutations, executions, worker jobs)
- **Ratio:** ~52% async (reflects event-driven architecture)
