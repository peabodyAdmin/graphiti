# Phase 6: 05-openapi.md Edge-Primacy Migration

## Context

The OpenAPI document defines the REST API contract. Schema properties remain as data transfer fields, but their **descriptions** must express edge-primacy semantics. This differs from prior phases where we removed property-based language entirely.

**Important:** This is a greenfield specification. No deprecation language. No migration notes.

**File to edit:** `/Users/robhitchens/Documents/projects/peabawdy/graphiti/aiden/docs/05-openapi.md`

---

## Guiding Principles

1. **Schema properties unchanged** — `userId`, `processId`, etc. remain as API contract
2. **Descriptions express edges** — Property descriptions reference the edge they represent
3. **Endpoint descriptions** — POST operations describe edge creation (sync/async)
4. **Greenfield** — No deprecation markers, no migration language
5. **Consistency** — Match terminology from phases 1-5

---

## Edits Required

### Edit 6.1: Conversation Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/Conversation`

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `userId` | (none or minimal) | "Owner identity; establishes `OWNED_BY` edge target (immutable)" |
| `processId` | "UI hint for preferred Process" | "Process hint; represents `DEFAULT_PROCESS` edge target (nullable)" |
| `activeEntities` | "Graphiti Entity UUIDs currently relevant" | "Entity UUIDs with active `HAS_ACTIVE_ENTITY` edges to this Conversation" |
| `parentConversationId` | (none) | "Fork source; `FORKED_FROM` edge target (immutable)" |
| `forkOriginTurnId` | (none) | "Fork origin Turn; stored on `FORKED_FROM` edge (immutable)" |
| `forkOriginAlternativeId` | (none) | "Fork origin Alternative; stored on `FORKED_FROM` edge (immutable)" |

---

### Edit 6.2: ConversationTurn Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/ConversationTurn`

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `conversationId` | (none) | "Parent Conversation; inverse of `HAS_TURN` edge (immutable)" |
| `parentTurnId` | (none or minimal) | "Parent Turn in tree; `CHILD_OF` edge target (immutable, nullable)" |
| `alternatives` | (none) | "Alternatives linked via `HAS_ALTERNATIVE` edges; minimum one required" |

---

### Edit 6.3: Alternative Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/Alternative`

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `episodeId` | (none or minimal) | "Graphiti Episode; `HAS_CONTENT` edge target (nullable until async binding completes)" |
| `processId` | "Process that created this (agent only)" | "Executing Process; `EXECUTED_BY` edge target (agent turns only, immutable)" |
| `inputContext.parentAlternativeId` | (none) | "Response target; `RESPONDS_TO` edge target (immutable)" |

---

### Edit 6.4: Summary Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/Summary`

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `conversationId` | (none) | "Parent Conversation; inverse of `HAS_SUMMARY` edge (immutable)" |
| `episodeId` | "Graphiti Episode UUID containing summary content" | "Summary content Episode; `HAS_CONTENT` edge target" |
| `sourceEpisodeIds` | "Episode UUIDs compressed into this Summary" | "Source Episodes; `SUMMARIZES` edge targets (immutable)" |
| `priorTurnId` | "Last Turn included in this summary" | "Boundary Turn; `COVERS_UP_TO` edge target (immutable)" |
| `createdBy` | (enum description) | "Attribution; if 'worker', establishes `CREATED_BY_PROCESS` edge" |

---

### Edit 6.5: Introspection Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/Introspection`

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `userId` | (none) | "Owner identity; `OWNED_BY` edge target (immutable)" |
| `episodeId` | (none) | "Introspection content Episode; `HAS_CONTENT` edge target" |

---

### Edit 6.6: Tool Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/Tool` (need to locate in document)

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `serviceId` | (current) | "Bound Service; `USES_SERVICE` edge target" |
| `secretId` | (current) | "Credential reference; `USES_SECRET` edge target (nullable)" |
| `ownerId` | (current) | "Owner identity; `OWNED_BY` edge target (immutable)" |

---

### Edit 6.7: Service Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/Service` (need to locate in document)

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `ownerId` | (current) | "Owner identity; `OWNED_BY` edge target (immutable)" |

---

### Edit 6.8: Secret Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/SecretMetadata` (need to locate in document)

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `userId` | (current) | "Owner identity; `OWNED_BY` edge target (immutable, derived from auth)" |

---

### Edit 6.9: ProcessStep Schema Property Descriptions

- [x] **Complete**

**Location:** `components/schemas/ProcessStep`

**Changes:**

| Property | Current Description | New Description |
|----------|---------------------|-----------------|
| `execution.toolId` | (current) | "Target Tool; `CALLS_TOOL` edge target (mode=tool)" |
| `execution.processId` | (current) | "Target Process; `CALLS_PROCESS` edge target (mode=subprocess)" |
| `dependsOn` | (current) | "Prerequisite steps; `DEPENDS_ON` edge targets" |

---

### Edit 6.10: POST Endpoint Edge Documentation

- [x] **Complete**

**Locations:** POST endpoint descriptions for key resources

Add edge creation documentation to these endpoints:

| Endpoint | Add to Description |
|----------|-------------------|
| `POST /conversations` | "Establishes `OWNED_BY` edge (sync) and optional `DEFAULT_PROCESS` edge" |
| `POST /conversations/{id}/turns` | "Establishes `HAS_TURN` edge, `CHILD_OF` edge (if parent), `HAS_ALTERNATIVE` edge (sync); triggers async `HAS_CONTENT` edge via EpisodeIngestionWorker" |
| `POST /conversations/{id}/turns/{turnId}/alternatives` | "Establishes `HAS_ALTERNATIVE` edge, `RESPONDS_TO` edge, `EXECUTED_BY` edge (sync); triggers async `HAS_CONTENT` edge" |
| `POST /conversations/{id}/turns/{turnId}/fork` | "Establishes `FORKED_FROM` edge with origin metadata, copies `HAS_ACTIVE_ENTITY` edges if requested" |
| `POST /conversations/{id}/working-memory/compress` | "Establishes `HAS_SUMMARY`, `SUMMARIZES`, `HAS_CONTENT`, `COVERS_UP_TO`, `CREATED_BY_PROCESS` edges" |

---

## Validation Checklist

- [x] Conversation schema properties reference edges in descriptions
- [x] ConversationTurn schema properties reference edges in descriptions
- [x] Alternative schema properties reference edges in descriptions
- [x] Summary schema properties reference edges in descriptions
- [x] Introspection schema properties reference edges in descriptions
- [x] Tool schema properties reference edges in descriptions
- [x] Service schema properties reference edges in descriptions
- [x] Secret schema properties reference edges in descriptions
- [x] ProcessStep schema properties reference edges in descriptions
- [x] POST endpoints document edge creation timing (sync/async)
- [x] No deprecation language anywhere
- [x] No migration/dual-write notes
- [x] Edge names match 19 canonical edges from foundation

---

## Constraints

1. **Schema structure unchanged** — Properties remain as API contract
2. **Only descriptions change** — No new properties, no removed properties
3. **No new endpoints** — Documentation migration only
4. **Preserve YAML structure** — No structural changes to OpenAPI document
5. **Entity.group_id unchanged** — Graphiti-managed property, not an Aiden edge

---

## Cross-File Dependencies

- **Depends on:** Phases 1–5 (edge definitions, patterns, event triggers)
- **Blocking:** Final validation

---

## Next Steps

- [x] Execute all edits (6.1–6.10)
- [x] Run validation checklist
- [x] Mark phase complete

---

## Completion Record

**Completed:** 2024-12-16
**Verified by:** Claude (systematic edit-by-edit review)
**Files modified:** `aiden/docs/05-openapi.md` (+35-7 lines)
**Notes:** Tool.secretId not present as direct property; credential alignment documented in connectionParams description per BR-SECRET-002B.
