```markdown
# Phase 3: 02-archtecture.md Edge-Primacy Migration

## Context

The foundation (`00-foundation.md`) and business rules (`01-business_rules.md`) documents have been migrated to edge-primacy. Use them as reference and examples if unsure of prior decisions. The architecture document describes event-driven patterns, episode binding, alternative cascades, context assembly, and compression—all currently using property-based language that must be converted to edge-based patterns.

**Important:** This is a greenfield specification. Use remove-don't-deprecate language. No migration paths, no "formerly known as," no backwards compatibility notes.

**File to edit:** `/Users/robhitchens/Documents/projects/peabawdy/graphiti/aiden/docs/02-architecture.md`

---

## Guiding Principles

1. **Edge-primacy:** Express structural relationships as Neo4j edges, not ID properties
2. **Remove-don't-deprecate:** Greenfield spec—no legacy terminology
3. **Semantic equivalence:** Same constraints, edge-based enforcement
4. **Match foundation doc:** Use only the 19 canonical edges

---

## Edge Type Reference

| Edge Type | From → To | Properties | Replaces |
|-----------|-----------|------------|----------|
| OWNED_BY | Service/Tool/Process/Secret/Conversation → User | created_at | ownerId, userId |
| USES_SERVICE | Tool → Service | connectionParams | serviceId |
| USES_SECRET | Tool → Secret | scope | secretId |
| DEFAULT_PROCESS | Conversation → Process | since | processId |
| FORKED_FROM | Conversation → Conversation | originTurn, originAlternative | parentConversationId, forkOriginTurnId, forkOriginAlternativeId |
| HAS_TURN | Conversation → Turn | sequence | conversationId |
| CHILD_OF | Turn → Turn | viaAlternative | parentTurnId |
| HAS_ALTERNATIVE | Turn → Alternative | isActive, sequence | embedded alternatives array |
| RESPONDS_TO | Alternative → Alternative | none | inputContext.parentAlternativeId |
| EXECUTED_BY | Alternative → Process | createdAt | processId |
| HAS_CONTENT | Alternative/Summary/Introspection → Episode | source, createdAt | episodeId |
| SUMMARIZES | Summary → Episode | order | sourceEpisodeIds |
| HAS_SUMMARY | Conversation → Summary | none | conversationId |
| COVERS_UP_TO | Summary → Turn | none | priorTurnId |
| CREATED_BY_PROCESS | Summary → Process | none | createdBy |
| HAS_ACTIVE_ENTITY | Conversation → Entity | addedAt, relevance | activeEntities |
| CALLS_TOOL | ProcessStep → Tool | timeout, interactionMode | toolId |
| CALLS_PROCESS | ProcessStep → Process | timeout | processId |
| DEPENDS_ON | ProcessStep → ProcessStep | order | dependsOn |

---

## Edits Required

### Edit 3.1: Episode Binding Lifecycle

- [*] **Complete**

**Location:** "Episode Binding Pattern" section and "Content Storage Pattern" section

**Current language (examples):**
- "Worker updates `Alternative.episodeId` once Graphiti confirms write"
- "Alternative.episodeId remains `null` until the ingestion worker finishes"
- "episodeUUID: ref"
- "name === 'Turn:{turn.uuid}'"

**Required changes:**
- Replace `episodeId = null` → `HAS_CONTENT edge not yet established`
- Replace "updates Alternative.episodeId" → "creates HAS_CONTENT edge to Episode"
- Replace "episodeUUID: ref" → "linked via HAS_CONTENT edge"
- Describe event-driven binding: `TurnCreated` event → worker creates Episode → worker creates `HAS_CONTENT` edge

**Transformations:**

| Before | After |
|--------|-------|
| `Worker updates Alternative.episodeId once Graphiti confirms write` | `Worker establishes HAS_CONTENT edge from Alternative to Episode once Graphiti confirms write` |
| `Alternatives still awaiting episodeId` | `Alternatives without HAS_CONTENT edges to Episodes` |
| `episodeId = null` | `HAS_CONTENT edge not yet established` |
| `episodeUUID: ref` | `linked via HAS_CONTENT edge` |

---

### Edit 3.2: Alternative Cascade Algorithm

- [*] **Complete**

**Location:** "Three-Phase Cascade Algorithm" section, "Cache Status & Lazy Regeneration" section, "WorkingMemory Assembly from User Selection" section

**Current language (examples):**
- `turn.alternatives.forEach(alt => ...)`
- `alt.isActive`
- `selectedAlt.inputContext.parentAlternativeId`
- `turn.alternatives.find(a => a.isActive)`
- `childAlt.inputContext.parentAlternativeId === activeAlt.id`

**Required changes:**
- Replace `turn.alternatives` array iteration → traverse `HAS_ALTERNATIVE` edges from Turn
- Replace `alt.isActive` property → `HAS_ALTERNATIVE.isActive` edge property
- Replace `inputContext.parentAlternativeId` → `RESPONDS_TO` edge target
- Use edge traversal functions in pseudocode

**Transformations:**

| Before | After |
|--------|-------|
| `turn.alternatives.forEach(alt => { alt.isActive = (alt.id === alternativeId); });` | `getAlternativesViaHasAlternative(turn).forEach(alt => { setHasAlternativeIsActive(turn, alt, alt.id === alternativeId); });` |
| `let requiredParentAltId = selectedAlt.inputContext.parentAlternativeId;` | `let requiredParentAlt = getRespondsToTarget(selectedAlt);` |
| `const parentActiveId = parentTurn?.alternatives.find(a => a.isActive)?.id;` | `const parentActiveAlt = getActiveAlternativeViaHasAlternative(parentTurn);` |
| `alternative.inputContext.parentAlternativeId === parentActiveId` | `getRespondsToTarget(alternative)?.id === parentActiveAlt?.id` |
| `const alt = turn.alternatives.find(a => a.id === altId && a.isActive);` | `const alt = getAlternativeViaHasAlternative(turn, altId); // Active check via isHasAlternativeActive(turn, alt)` |

---

### Edit 3.3: Context Assembly (WorkingMemory)

- [*] **Complete**

**Location:** "Context Assembly With Entities" section, "WorkingMemory Assembly from User Selection" section

**Current language (examples):**
- "WorkingMemory.immediateEpisodes"
- "episodeId in active path"
- "summaries (cached Summary IDs)"
- "activeEntities (EntityReference objects)"
- References to stored arrays/fields

**Required changes:**
- Clarify WorkingMemory is a **computed view** (no persistent WorkingMemory node or edges)
- Assembly traverses: `HAS_TURN` → `HAS_ALTERNATIVE` (isActive=true) → `HAS_CONTENT` → Episodes
- Summaries gathered via: `HAS_SUMMARY` edges
- Active entities gathered via: `HAS_ACTIVE_ENTITY` edges
- Introspection context: separate query by user scope

**Transformation:**

Before:
```
WorkingMemory Builder (per conversation turn)
   |- immediateEpisodes (latest Episode UUIDs from active path)
   |- summaries (cached Summary IDs)
   |- activeEntities (EntityReference objects)
```

After:
```
WorkingMemory Builder (computed per conversation turn)
   |- immediateEpisodes: Traverse HAS_TURN → HAS_ALTERNATIVE (isActive=true) → HAS_CONTENT → Episode
   |- summaries: Traverse HAS_SUMMARY edges from Conversation
   |- activeEntities: Traverse HAS_ACTIVE_ENTITY edges from Conversation
   |- introspectionContext: Query Introspection nodes by user scope via OWNED_BY
```

---

### Edit 3.4: Compression & Summarization

- [*] **Complete**

**Location:** "Compression Algorithm" section, "Context Compression Strategy" section

**Current language (examples):**
- "Summary references source Episode UUIDs"
- "sourceEpisodeIds"
- "createdBy"
- "Summary.compressionLevel = max(sourceEpisode.compressionLevel) + 1"

**Required changes:**
- Replace "source Episode UUIDs" → `SUMMARIZES` edges to Episodes
- Replace "sourceEpisodeIds" → `SUMMARIZES` edge traversal
- Replace "createdBy" reference → `CREATED_BY_PROCESS` edge
- Describe compression lineage using edge terms

**Transformation:**

Before:
```
3. Create Summary entity
   - Summary content stored as new Episode in Graphiti (source='summary')
   - Summary references source Episode UUIDs
   - CompressionLevel = max(source Episodes) + 1
```

After:
```
3. Create Summary node with edges
   - Create HAS_CONTENT edge to new Episode (source='summary')
   - Create SUMMARIZES edges to each source Episode (order property preserves sequence)
   - Create HAS_SUMMARY edge from Conversation to Summary
   - Create COVERS_UP_TO edge to boundary Turn
   - Create CREATED_BY_PROCESS edge to compression Process
   - compressionLevel = max(SUMMARIZES targets' compressionLevel) + 1
```

---

### Edit 3.5: Process Ownership

- [*] **Complete**

**Location:** "Process Ownership: UI Hint vs Execution Truth" section

**Current language (examples):**
- `Conversation.processId` (mutable UI hint)
- `Alternative.processId` (immutable execution record)
- `conversation.processId = selectedProcessId`

**Required changes:**
- Replace `Conversation.processId` → `DEFAULT_PROCESS` edge
- Replace `Alternative.processId` → `EXECUTED_BY` edge
- Update code examples to use edge operations

**Transformations:**

Before:
```typescript
Conversation {
  processId: string | null  // mutable UI hint
}

Alternative {
  processId: string | null  // immutable execution record
}
```

After:
```typescript
Conversation {
  // Process preference expressed via DEFAULT_PROCESS edge (mutable target)
}

Alternative {
  // Execution truth expressed via EXECUTED_BY edge (immutable target)
}
```

Before:
```typescript
conversation.processId = selectedProcessId;
```

After:
```typescript
createOrUpdateDefaultProcessEdge(conversation.id, selectedProcessId);
```

---

### Edit 3.6: Error Context Exception

- [*] **Complete**

**Location:** "Error Propagation" section in ProcessStep Execution Engine

**Current language:**
- `"toolId": "tool-anthropic-claude"`
- `"serviceId": "service-anthropic"`

**Required changes:**
- These ID values in error JSON payloads are acceptable (logging/debugging identifiers)
- Ensure surrounding prose uses edge language when describing relationships
- No changes needed if context is clearly error payload values

---

### Edit 3.7: Secret & Service Ownership Validation

- [*] **Complete**

**Location:** "Secret Ownership & Access Control" section, "Runtime Dependency Validation" section

**Current language (examples):**
- "secretId belongs to the same userId as the Tool"
- "owner unshares Tool (shared=true → false)"
- References to `ownerId`, `userId` comparisons

**Required changes:**
- Replace ownership comparisons with `OWNED_BY` edge target language
- Replace "userId" references with `OWNED_BY` edge traversal

**Transformation:**

Before:
```
Tool execution validates secretId belongs to the same userId as the Tool and the Conversation
```

After:
```
Tool execution validates the Secret's OWNED_BY edge targets the same User as the Tool's OWNED_BY edge and the Conversation's OWNED_BY edge
```

---

## Property-to-Edge Scan Table

Scan the document for these property references and convert to edge language:

| Property Reference | Edge Replacement |
|-------------------|------------------|
| `episodeId` | `HAS_CONTENT` edge |
| `inputContext.parentAlternativeId` | `RESPONDS_TO` edge target |
| `isActive` (on Alternative) | `HAS_ALTERNATIVE.isActive` edge property |
| `alternatives[]` array | `HAS_ALTERNATIVE` edges from Turn |
| `sourceEpisodeIds` | `SUMMARIZES` edges |
| `createdBy` (on Summary) | `CREATED_BY_PROCESS` edge |
| `Conversation.processId` | `DEFAULT_PROCESS` edge |
| `Alternative.processId` | `EXECUTED_BY` edge |
| `ownerId` / `userId` comparisons | `OWNED_BY` edge target comparisons |
| `secretId` validation | `USES_SECRET` + `OWNED_BY` edge traversal |
| `toolId`, `serviceId` (structural) | `CALLS_TOOL`, `USES_SERVICE` edges |

**Exception:** `toolId`, `serviceId`, `processId` in error payloads (JSON logging) are acceptable as string identifiers—they're values, not relationship expressions.

---

## Validation Checklist

- [*] Episode binding flow describes `HAS_CONTENT` edge creation, not `episodeId` assignment
- [*] Cascade algorithm code uses edge traversal functions
- [*] `isActive` references use `HAS_ALTERNATIVE.isActive` edge property language
- [*] WorkingMemory described as computed traversal (no stored WorkingMemory node)
- [*] Compression lineage uses: `HAS_SUMMARY`, `SUMMARIZES`, `HAS_CONTENT`, `COVERS_UP_TO`, `CREATED_BY_PROCESS`
- [*] Process ownership uses `DEFAULT_PROCESS` and `EXECUTED_BY` edges
- [*] Ownership validation uses `OWNED_BY` edge target comparisons
- [*] No residual `episodeId`, `parentAlternativeId`, `sourceEpisodeIds`, or `createdBy` property references
- [*] Edge names match the 19 canonical edges exactly

---

## Constraints

1. **No scope creep** — Only edit `02-archtecture.md`
2. **No invented edges** — Use only the 19 canonical edges
3. **No deprecation language** — This is a greenfield spec
4. **Preserve semantics** — Same behavior, different expression
5. **Ask if unclear** — Don't guess on ambiguous cases

---

## Cross-File Dependencies

- **Depends on:** Phases 1–2 (edge definitions in foundation, BR alignment in business rules)
- **Blocking:** Phases 4–6 (AsyncAPI/OpenAPI must align with these patterns)

---

## Next Steps

- [*] Execute all edits (3.1–3.7)
- [*] Run validation checklist
- [*] Mark phase complete
- [ ] Proceed to `phase4-endpoint-classification.md`
```
