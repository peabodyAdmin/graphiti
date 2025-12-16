# Phase 4: 03-endpoint-classification.md Edge-Primacy Migration

## Context

The endpoint classification document catalogs sync vs async behavior for all API endpoints. The rationale text in several places uses property-based language that must be converted to edge-based patterns for consistency with phases 1-3.

**Important:** This is a greenfield specification. Remove-don't-deprecate. No migration language.

**File to edit:** `/Users/robhitchens/Documents/projects/peabawdy/graphiti/aiden/docs/03-endpoint-classification.md`

---

## Guiding Principles

1. **Edge-primacy:** Rationale text references edges, not ID properties
2. **Greenfield:** No migration or legacy terminology
3. **Minimal changes:** Document structure is correct; only rationale text needs updating
4. **Consistency:** Match terminology from foundation and architecture docs

---

## Edits Required

### Edit 4.1: Secrets Rationale

- [*] **Complete**

**Location:** Secrets table, Rationale column

**Changes:**

| Endpoint | Current Rationale | New Rationale |
|----------|-------------------|---------------|
| GET `/secrets` | "Owner-scoped metadata read (filters by userId)" | "Owner-scoped metadata read (filters by `OWNED_BY` edge)" |
| GET `/secrets/{id}` | "Owner-only metadata (non-owner → 404)" | "Owner-only metadata via `OWNED_BY` (non-owner → 404)" |
| POST `/secrets` | "Create encrypted secret (userId from auth; event published)" | "Create encrypted secret (establishes `OWNED_BY` edge from auth context; event published)" |
| PUT `/secrets/{id}` | "Rotate encrypted value (owner-only; event published)" | "Rotate encrypted value (`OWNED_BY` validation; event published)" |
| DELETE `/secrets/{id}` | "Delete secret (owner-only; event published)" | "Delete secret (`OWNED_BY` validation; event published)" |

---

### Edit 4.2: Conversations Rationale

- [*] **Complete**

**Location:** Conversations table, Rationale column

**Changes:**

| Endpoint | Current Rationale | New Rationale |
|----------|-------------------|---------------|
| PUT `/conversations/{id}` | "Update metadata only (title, processId hint)" | "Update metadata only (title, `DEFAULT_PROCESS` edge)" |
| POST `/conversations/{id}/turns` | "Create Turn (Episode creation)" | "Create Turn (async `HAS_CONTENT` edge to Episode)" |

---

### Edit 4.3: Turns & Alternatives Rationale

- [*] **Complete**

**Location:** Turns & Alternatives table, Rationale column

**Changes:**

| Endpoint | Current Rationale | New Rationale |
|----------|-------------------|---------------|
| POST `.../alternatives` | "Create alternative (Episode + possible execution)" | "Create alternative (async `HAS_CONTENT` edge + `EXECUTED_BY` edge if agent)" |

---

### Edit 4.4: Summaries Rationale

- [*] **Complete**

**Location:** Summaries table, Rationale column

**Changes:**

| Endpoint | Current Rationale | New Rationale |
|----------|-------------------|---------------|
| PUT `.../summaries/{summaryId}` | "Update summary episode binding" | "Update summary `HAS_CONTENT` edge binding" |

---

## Validation Checklist

- [*] No `userId` references remain in rationale text
- [*] No `processId` references remain in rationale text  
- [*] No bare `episode` references where edge relationship is meant
- [*] Edge names match the 19 canonical edges
- [*] No migration or legacy language

---

## Constraints

1. **Table structure unchanged** — Only edit Rationale column text
2. **No invented edges** — Use only canonical edges
3. **No classification changes** — Sync/async designations are correct
4. **Preserve brevity** — Rationale text stays concise

---

## Cross-File Dependencies

- **Depends on:** Phases 1–3 (edge definitions, patterns)
- **Blocking:** Phases 5–6 (AsyncAPI/OpenAPI reference these classifications)

---

## Next Steps

- [*] Execute all edits (4.1–4.4)
- [*] Run validation checklist
- [*] Mark phase complete
