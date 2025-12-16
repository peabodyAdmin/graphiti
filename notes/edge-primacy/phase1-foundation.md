# Phase 1: 00-foundation.md Updates

## Context
- This is phase 1 of multistep process to convert _most_ of the property ids with edge-based construction. 
- Replace property-based pointers with graph edges in `00-foundation.md`.
- Dual-write during migration (properties + edges).
- Documentation update only.

## Guiding Principles

1. **Edge-primacy**: Replace property pointers (`*Id` fields) with graph edges. Properties point to nothing; edges connect things.

2. **Deprecate, don't delete**: Mark replaced properties as deprecated with their edge replacement noted. Removal happens later.

3. **group_id is untouchable**: Graphiti uses `group_id` for Episode/Entity scoping. It remains a property. No edge. No discussion.

4. **WorkingMemory is computed**: No edges. Built at runtime via traversal.

5. **19 edges, no more**: The reference table is authoritative. Don't invent edges.

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

## Edge Creation Timing
| Edge Type | Timing | Dependency |
|-----------|--------|------------|
| OWNED_BY | Sync | None |
| USES_SERVICE | Sync | Service must exist |
| USES_SECRET | Sync | Secret must exist |
| DEFAULT_PROCESS | Sync | Process must exist |
| FORKED_FROM | Sync | Parent Conversation must exist |
| HAS_TURN | Sync | Conversation must exist |
| CHILD_OF | Sync | Parent Turn must exist |
| HAS_ALTERNATIVE | Sync | Turn must exist |
| RESPONDS_TO | Sync | Parent Alternative must exist |
| EXECUTED_BY | Sync | Process must exist |
| HAS_CONTENT | Async | Graphiti Episode UUID required |
| SUMMARIZES | Async | Source Episodes must exist |
| HAS_SUMMARY | Sync | Summary node created |
| COVERS_UP_TO | Sync | Turn must exist |
| CREATED_BY_PROCESS | Sync | Process must exist |
| HAS_ACTIVE_ENTITY | Sync | Entity must exist |
| CALLS_TOOL | Sync | Tool must exist |
| CALLS_PROCESS | Sync | Target Process must exist |
| DEPENDS_ON | Sync | Dependent step must exist |

## Architectural Decisions
1. Alternatives as Nodes: promote alternatives to nodes with edges.
2. Secrets: edge with vault reference, no credentials in graph.
3. WorkingMemory: computed via traversal, no persistent edges.
4. Dual-Write: keep properties during migration, document deprecation (group_id remains a property for Graphiti compatibility).

## Edits for 00-foundation.md
- [x] ### Edit 1.1: Service Entity (ownerId → OWNED_BY)
  - Location: Service entity definition.
  - Replace ownerId property with deprecated note; add relationship block for OWNED_BY.
- [x] ### Edit 1.2: Tool Entity - Service/Secret Dependency
  - Location: Tool entity definition.
  - Deprecate ownerId/serviceId/connectionParams.secretId; add OWNED_BY, USES_SERVICE, USES_SECRET relationships and vault note.
- [x] ### Edit 1.3: Conversation Entity - Structure & References
  - Deprecate userId/processId/activeEntities/parentConversationId/forkOrigin*; add OWNED_BY, DEFAULT_PROCESS, HAS_ACTIVE_ENTITY, FORKED_FROM, HAS_TURN relationships.
- [x] ### Edit 1.4: ConversationTurn Entity - Structure & Alternatives
  - Deprecate conversationId/parentTurnId/alternatives array; add HAS_TURN, CHILD_OF, HAS_ALTERNATIVE edges and sequences in edges.
- [x] ### Edit 1.5: Summary Entity - Lineage
  - Deprecate episodeId/sourceEpisodeIds/priorTurnId/createdBy; add HAS_SUMMARY, SUMMARIZES, HAS_CONTENT, COVERS_UP_TO, CREATED_BY_PROCESS relationships.
- [x] ### Edit 1.6: WorkingMemory Entity - Computed View
  - Clarify no stored edges; computed via traversal of HAS_ALTERNATIVE/HAS_SUMMARY/HAS_ACTIVE_ENTITY/HAS_CONTENT.
- [x] ### Edit 1.7: ProcessStep - Dependencies
  - Deprecate toolId/processId/dependsOn arrays; add CALLS_TOOL/CALLS_PROCESS/DEPENDS_ON edges.

## Validation Checklist
- [x] All deprecated properties marked and replacement edges documented.
- [x] All relationship blocks added with correct edge types/properties.
- [x] Dual-write notes present for ownerId and other props kept temporarily.
- [x] Edge type names match reference table.
- [x] Context assembly/WorkingMemory described as computed (no edges).

## Cross-File Dependencies
- Depends on: None.
- Blocking: Subsequent phases assume edge definitions described here.

## Next Steps
- [ ] Mark phase complete in README when all edits/validation done.
- [ ] Proceed to `phase2-business-rules.md` after completion.
