# Phase 4: 03-endpoint-classification.md Updates

## Context
- Ensure endpoint classifications reflect edge-based model (ids -> edge creations, async patterns).

## Edge Type Reference
(full table; same as prior phases)

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

## Edits for 03-endpoint-classification.md
- [ ] ### Edit 4.1: Async vs Sync Classification
  - Clarify mutation endpoints imply edge creation (e.g., POST Tool creates USES_SERVICE/OWNED_BY edges); reads remain sync; async episode binding noted.

## Validation Checklist
- [ ] Classifications mention edge creation where relevant.
- [ ] Async flows (episode binding, alternative creation) noted for edge timing.
- [ ] Edge names consistent with reference table.

## Cross-File Dependencies
- Depends on: Phases 1–3 patterns.
- Blocking: AsyncAPI/OpenAPI phases use these classifications.

## Next Steps
- [ ] Mark phase complete after edits/validation.
- [ ] Proceed to `phase5-async-api.md`.
