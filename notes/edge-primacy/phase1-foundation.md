# Phase 1: 00-foundation.md Updates

## Context
- Replace property-based pointers with graph edges in `00-foundation.md`.
- Dual-write during migration (properties + edges).
- Documentation update only.

## Edge Type Reference
| Edge Type | From → To | Properties | Replaces |
|-----------|-----------|------------|----------|
| OWNED_BY | Service/Tool/Process/Template/Secret/Conversation → User | created_at | ownerId, userId |
| INSTANTIATED_FROM | Service/Tool → Template | at | serviceTemplateId, toolTemplateId |
| USES_SERVICE | Tool → Service | connectionParams | serviceId |
| USES_SECRET | Tool → Secret | scope | secretId |
| DEFAULT_PROCESS | Conversation → Process | since | processId |
| FORKED_FROM | Conversation → Conversation | originTurn, originAlternative | parentConversationId, forkOriginTurnId, forkOriginAlternativeId |
| HAS_TURN | Conversation → Turn | sequence | conversationId |
| CHILD_OF | Turn → Turn | viaAlternative | parentTurnId |
| HAS_ALTERNATIVE | Turn → Alternative | isActive, sequence | embedded alternatives array |
| RESPONDS_TO | Alternative → Alternative | none | inputContext.parentAlternativeId |
| EXECUTED_BY | Alternative → Process | createdAt | processId |
| BOUND_TO_EPISODE | Alternative/Summary/Introspection → Episode | source, createdAt | episodeId |
| SUMMARIZES | Summary → Episode | order | sourceEpisodeIds |
| HAS_SUMMARY | Conversation → Summary | none | conversationId |
| HAS_CONTENT | Summary/Introspection → Episode | none | episodeId |
| COVERS_UP_TO | Summary → Turn | none | priorTurnId |
| CREATED_BY_PROCESS | Summary → Process | none | createdBy |
| HAS_ACTIVE_ENTITY | Conversation → Entity | addedAt, relevance | activeEntities |
| SCOPED_TO | Episode/Entity → Conversation/User | created_at | group_id |
| CALLS_TOOL | ProcessStep → Tool | timeout, interactionMode | toolId |
| CALLS_PROCESS | ProcessStep → Process | timeout | processId |
| DEPENDS_ON | ProcessStep → ProcessStep | order | dependsOn |
| FOR_ENTITY | MetricValue → Service/Tool/Process/Conversation | dimensions | entityId |
| OF_METRIC | MetricValue → MetricDefinition | none | metricId |

## Architectural Decisions
1. Graphiti SCOPED_TO: dual-write `group_id` + `SCOPED_TO` edge.
2. Alternatives as Nodes: promote alternatives to nodes with edges.
3. Secrets: edge with vault reference, no credentials in graph.
4. WorkingMemory: computed via traversal, no persistent edges.
5. Dual-Write: keep properties during migration, document deprecation.

## Edits for 00-foundation.md
- [ ] ### Edit 1.1: Service Entity (ownerId → OWNED_BY)
  - Location: Service entity definition.
  - Replace ownerId property with deprecated note; add relationship block for OWNED_BY.
- [ ] ### Edit 1.2: Tool Entity - Service/Secret Dependency
  - Location: Tool entity definition.
  - Deprecate ownerId/serviceId/connectionParams.secretId; add OWNED_BY, USES_SERVICE, USES_SECRET relationships and vault note.
- [ ] ### Edit 1.3: Process Entity - Template Provenance
  - Location: Process entity and Service template references.
  - Deprecate ownerId/serviceTemplateId; add OWNED_BY and INSTANTIATED_FROM relationships.
- [ ] ### Edit 1.4: Conversation Entity - Structure & References
  - Deprecate userId/processId/activeEntities/parentConversationId/forkOrigin*; add OWNED_BY, DEFAULT_PROCESS, HAS_ACTIVE_ENTITY, FORKED_FROM, HAS_TURN relationships.
- [ ] ### Edit 1.5: ConversationTurn Entity - Structure & Alternatives
  - Deprecate conversationId/parentTurnId/alternatives array; add HAS_TURN, CHILD_OF, HAS_ALTERNATIVE edges and sequences in edges.
- [ ] ### Edit 1.6: Episode Entity - Graphiti Scoping
  - Keep `group_id` (Graphiti requirement); add `SCOPED_TO` edge; dual-write note and validation query.
- [ ] ### Edit 1.7: Entity Entity - Graphiti Scoping
  - Similar to Episode: SCOPED_TO edge, dual-write note.
- [ ] ### Edit 1.8: Summary Entity - Lineage
  - Deprecate episodeId/sourceEpisodeIds/priorTurnId/createdBy; add HAS_SUMMARY, SUMMARIZES, HAS_CONTENT, COVERS_UP_TO, CREATED_BY_PROCESS relationships.
- [ ] ### Edit 1.9: WorkingMemory Entity - Computed View
  - Clarify no stored edges; computed via traversal of HAS_ALTERNATIVE/HAS_SUMMARY/HAS_ACTIVE_ENTITY/BOUND_TO_EPISODE.
- [ ] ### Edit 1.10: ProcessStep - Dependencies
  - Deprecate toolId/processId/dependsOn arrays; add CALLS_TOOL/CALLS_PROCESS/DEPENDS_ON edges.

## Validation Checklist
- [ ] All deprecated properties marked and replacement edges documented.
- [ ] All relationship blocks added with correct edge types/properties.
- [ ] Dual-write notes present for ownerId/group_id and other props kept temporarily.
- [ ] Edge type names match reference table.
- [ ] Context assembly/WorkingMemory described as computed (no edges).

## Cross-File Dependencies
- Depends on: None.
- Blocking: Subsequent phases assume edge definitions described here.

## Next Steps
- [ ] Mark phase complete in README when all edits/validation done.
- [ ] Proceed to `phase2-business-rules.md` after completion.
