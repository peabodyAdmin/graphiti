# Phase 5: 04-async-api.md Updates

## Context
- Update AsyncAPI to express edge-intent events and remove property pointer semantics.

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

## Edits for 04-async-api.md
- [ ] ### Edit 5.1: TurnCreated Event
  - Document HAS_TURN/CHILD_OF edges emitted instead of conversationId/parentTurnId properties.
- [ ] ### Edit 5.2: EpisodeCreated Event
  - Event payload carries Episode UUID; consumers create BOUND_TO_EPISODE + SCOPED_TO edges; avoid group_id+name matching.
- [ ] ### Edit 5.3: AlternativeCreated Event
  - New event documenting HAS_ALTERNATIVE/RESPONDS_TO/EXECUTED_BY edges.
- [ ] ### Edit 5.4: CompressionCompleted Event
  - Emit HAS_SUMMARY, SUMMARIZES, HAS_CONTENT, COVERS_UP_TO, CREATED_BY_PROCESS edge intents.

## Validation Checklist
- [ ] Events describe edge creation intents, not property pointers.
- [ ] Episode binding marked async, event-driven.
- [ ] Edge names consistent with reference table.
- [ ] Dual-write notes present where relevant.

## Cross-File Dependencies
- Depends on: Phases 1–4 patterns.
- Blocking: OpenAPI alignment in Phase 6.

## Next Steps
- [ ] Mark phase complete after edits/validation.
- [ ] Proceed to `phase6-openapi.md`.
