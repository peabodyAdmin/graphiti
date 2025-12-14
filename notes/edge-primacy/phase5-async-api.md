# Phase 5: 04-async-api.md Updates

## Context
- Update AsyncAPI to express edge-intent events and remove property pointer semantics.

## Edge Type Reference
(full table; same as prior phases)

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

## Architectural Decisions
1. Alternatives as nodes.
2. Secrets via vault edge.
3. WorkingMemory computed.
4. Dual-write during migration (group_id remains property-level for Graphiti).

## Edits for 04-async-api.md
- [ ] ### Edit 5.1: TurnCreated Event
  - Document HAS_TURN/CHILD_OF edges emitted instead of conversationId/parentTurnId properties.
- [ ] ### Edit 5.2: EpisodeCreated Event
  - Event payload carries Episode UUID; consumers create HAS_CONTENT edges; avoid group_id+name matching.
- [ ] ### Edit 5.3: AlternativeCreated Event
  - Extend existing alternative.* channels with edge-intent fields (HAS_ALTERNATIVE/RESPONDS_TO/EXECUTED_BY); no new event shape, no duplication.
- [ ] ### Edit 5.4: CompressionCompleted Event
  - Emit HAS_SUMMARY, SUMMARIZES, HAS_CONTENT, COVERS_UP_TO, CREATED_BY_PROCESS edge intents.

## Validation Checklist
- [ ] Events describe edge creation intents, not property pointers.
- [ ] Episode binding marked async, event-driven.
- [ ] Edge names consistent with reference table.

## Cross-File Dependencies
- Depends on: Phases 1–4 patterns.
- Blocking: OpenAPI alignment in Phase 6.

## Next Steps
- [ ] Mark phase complete after edits/validation.
- [ ] Proceed to `phase6-openapi.md`.
