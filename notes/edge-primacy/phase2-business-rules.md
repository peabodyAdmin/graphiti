# Phase 2: 01-business_rules.md Updates

## Context
- Replace property-based rules with edge-based semantics in `01-business_rules.md`.
- Document dual-write where properties remain during migration.

## Edge Type Reference
(same as Phase 1; include full table for self-contained use)

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
1. Graphiti SCOPED_TO dual-write.
2. Alternatives as nodes.
3. Secrets via vault edge.
4. WorkingMemory computed.
5. Dual-write during migration.

## Edits for 01-business_rules.md
- [ ] ### Edit 2.1: BR-SHARE-001 (Ownership Validation)
  - Update rule language to reference OWNED_BY edge; keep ownerId as dual-write note.
- [ ] ### Edit 2.2: BR-SHARE-007 (Service Sharing)
  - Reference USES_SERVICE edge for dependency validation; remove serviceId property reliance.
- [ ] ### Edit 2.3: BR-SECRET-002B (Secret Access)
  - Use USES_SECRET edge + vault pattern; ownerId checks via OWNED_BY edges.
- [ ] ### Edit 2.4: BR-CONVERSATION-* (Conversation Structure)
  - Use HAS_TURN/CHILD_OF/FORKED_FROM edges; deprecate conversationId/parentTurnId pointers.
- [ ] ### Edit 2.5: BR-ALTERNATIVE-* (Alternative Cascade)
  - Cascade via RESPONDS_TO edges, not inputContext.parentAlternativeId property parsing.
- [ ] ### Edit 2.6: BR-EPISODE-002 (User-Scoped Episodes)
  - Dual-write group_id + SCOPED_TO; validation rule references edge.

## Validation Checklist
- [ ] All rules reference edges, not properties, with dual-write notes where necessary.
- [ ] Ownership/sharing rules align to OWNED_BY/USES_SERVICE/USES_SECRET edges.
- [ ] Cascade rules use RESPONDS_TO.
- [ ] Episode scoping uses SCOPED_TO + group_id dual-write.
- [ ] Edge names match reference table.

## Cross-File Dependencies
- Depends on: Phase 1 edge definitions.
- Blocking: Later phases assume BRs reference edges.

## Next Steps
- [ ] Mark phase complete when edits/validation done.
- [ ] Proceed to `phase3-architecture.md`.
