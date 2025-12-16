# Phase 5: 04-async-api.md Edge-Primacy Migration

## Context

The AsyncAPI document specifies all event schemas and flows. Channel descriptions and message triggers use property-based language (`userId`, `episodeId`, `processId`) that must be converted to edge-based patterns for consistency with phases 1-4.

**Important:** This is a greenfield specification. Remove-don't-deprecate. No migration language.

**File to edit:** `/Users/robhitchens/Documents/projects/peabawdy/graphiti/aiden/docs/04-async-api.md`

---

## Guiding Principles

1. **Edge-primacy:** Descriptions reference edges, not ID properties
2. **Payload fields unchanged:** `userId` etc. remain as data fields — only descriptions change
3. **Greenfield:** No migration or dual-write terminology
4. **Consistency:** Match terminology from foundation, business rules, and architecture docs

---

## Edits Required

### Edit 5.1: Secret Channel Descriptions

- [*] **Complete**

**Locations:** 4 channel descriptions in `channels:` section

**Changes:**

| Channel | Current Description | New Description |
|---------|---------------------|-----------------|
| `secret.creation.requested` | "includes `userId` for owner scoping and subscriber filtering" | "includes `OWNED_BY` edge target for owner scoping and subscriber filtering" |
| `secret.created` | "payload carries owning `userId` and never includes plaintext" | "payload carries `OWNED_BY` edge target and never includes plaintext" |
| `secret.rotated` | "includes owning `userId` for downstream filtering" | "includes `OWNED_BY` edge target for downstream filtering" |
| `secret.deleted` | "retains owning `userId`" | "retains `OWNED_BY` edge target" |

---

### Edit 5.2: Summary Channel Description

- [*] **Complete**

**Location:** `summary.updated` channel description

**Change:**

| Current | New |
|---------|-----|
| "SummaryWorker updated Summary episode binding" | "SummaryWorker updated Summary `HAS_CONTENT` edge binding" |

---

### Edit 5.3: TurnCreated Message Triggers

- [*] **Complete**

**Location:** `TurnCreated` message in `components/messages`

**Current x-triggers:**
```yaml
x-triggers:
  - Update operation status to 'completed'
  - Notify subscribers via webhooks
```

**New x-triggers:**
```yaml
x-triggers:
  - Update operation status to 'completed'
  - Establish HAS_TURN edge (Conversation → Turn)
  - Establish CHILD_OF edge (Turn → parent Turn) if parentTurnId provided
  - Establish HAS_ALTERNATIVE edge (Turn → Alternative) for initial alternative
  - Notify subscribers via webhooks
```

---

### Edit 5.4: AlternativeCreated Message Triggers

- [*] **Complete**

**Location:** `AlternativeCreated` message in `components/messages`

**Current x-triggers:**
```yaml
x-triggers:
  - Update operation status to 'completed'
  - Notify subscribers via webhooks
```

**New x-triggers:**
```yaml
x-triggers:
  - Update operation status to 'completed'
  - Establish HAS_ALTERNATIVE edge (Turn → Alternative)
  - Establish RESPONDS_TO edge (Alternative → parent Alternative) if responding to prior turn
  - Establish EXECUTED_BY edge (Alternative → Process) if agent turn
  - Trigger async HAS_CONTENT edge creation (Alternative → Episode) via EpisodeIngestionWorker
  - Notify subscribers via webhooks
```

---

### Edit 5.5: ContextCompressed Message Triggers

- [*] **Complete**

**Location:** `ContextCompressed` message in `components/messages`

**Current x-triggers:**
```yaml
x-triggers:
  - Update operation status to 'completed'
  - Notify subscribers via webhooks
```

**New x-triggers:**
```yaml
x-triggers:
  - Update operation status to 'completed'
  - Establish HAS_SUMMARY edge (Conversation → Summary)
  - Establish SUMMARIZES edges (Summary → source Episodes)
  - Establish HAS_CONTENT edge (Summary → Episode) for summary content
  - Establish COVERS_UP_TO edge (Summary → boundary Turn)
  - Establish CREATED_BY_PROCESS edge (Summary → compression Process)
  - Notify subscribers via webhooks
```

---

### Edit 5.6: Business Rule Mapping Descriptions

- [*] **Complete**

**Location:** `x-business-rule-mappings` section

**Changes:**

| Rule | Current `enforced-by` | New `enforced-by` |
|------|----------------------|-------------------|
| BR-SECRET-002A | "SecretCreationRequested user scoping (userId immutable and set from auth)" | "SecretCreationRequested user scoping (`OWNED_BY` edge target immutable, derived from auth)" |
| BR-SECRET-002B | "ProcessExecutionWorker Tool invocation guard (secretId/userId alignment)" | "ProcessExecutionWorker Tool invocation guard (`OWNED_BY` edge alignment between Secret, Tool, and Conversation)" |

---

## Validation Checklist

- [*] No bare `userId` in channel descriptions (should be `OWNED_BY` edge target)
- [*] No bare `episodeId` in descriptions (should be `HAS_CONTENT` edge)
- [*] TurnCreated triggers include `HAS_TURN`, `CHILD_OF`, `HAS_ALTERNATIVE` edges
- [*] AlternativeCreated triggers include `HAS_ALTERNATIVE`, `RESPONDS_TO`, `EXECUTED_BY`, `HAS_CONTENT` edges
- [*] ContextCompressed triggers include all 5 compression edges
- [*] Business rule mappings reference edges, not ID properties
- [*] No migration or dual-write language
- [*] Edge names match the 19 canonical edges

---

## Constraints

1. **Payload schemas unchanged** — `userId` etc. remain as data fields in schemas
2. **Channel addresses unchanged** — Only descriptions and triggers modified
3. **No invented edges** — Use only canonical edges from foundation
4. **Preserve YAML structure** — No structural changes to AsyncAPI document

---

## Cross-File Dependencies

- **Depends on:** Phases 1–4 (edge definitions, patterns, endpoint classifications)
- **Blocking:** Phase 6 (OpenAPI references these event schemas)

---

## Next Steps

- [*] Execute all edits (5.1–5.6)
- [*] Run validation checklist
- [*] Mark phase complete
