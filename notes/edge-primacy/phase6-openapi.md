# Phase 6: 05-openapi.md Updates

## Context
- Update OpenAPI schemas to represent edges (relationship intent) instead of property pointers.
- Document dual-write/deprecation clearly.

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

## Edits for 05-openapi.md
- [ ] ### Edit 6.1: Service Schema
  - Mark ownerId/serviceTemplateId deprecated; add OWNED_BY and INSTANTIATED_FROM notes; schema comments include relationships.
- [ ] ### Edit 6.2: Tool Schema
  - Deprecate ownerId/serviceId/secretId props; note USES_SERVICE/USES_SECRET edges and vault pattern.
- [ ] ### Edit 6.3: Conversation Schema
  - Deprecate processId/activeEntities/parentConversationId/forkOrigin*; add DEFAULT_PROCESS, HAS_ACTIVE_ENTITY, FORKED_FROM, HAS_TURN edges.
- [ ] ### Edit 6.4: Turn Schema
  - Deprecate conversationId/parentTurnId/alternatives array; add HAS_TURN, CHILD_OF, HAS_ALTERNATIVE edges; episode binding via BOUND_TO_EPISODE.
- [ ] ### Edit 6.5: Alternative Schema
  - Make alternatives nodes; include RESPONDS_TO/EXECUTED_BY/BOUND_TO_EPISODE; deprecate embedded fields.
- [ ] ### Edit 6.6: Add Relationship Endpoints
  - Document GET endpoints for related nodes (e.g., /services/{id}/relationships).
- [ ] ### Edit 6.7: Update POST Endpoints to Document Edge Creation
  - Each POST describes which edges are created synchronously (ownership, dependencies, structure) and which are async (episode binding).

## Validation Checklist
- [ ] All schemas mark deprecated properties with replacements.
- [ ] Relationship descriptions reference correct edge types.
- [ ] POST endpoint docs call out edge creation timing (sync/async).
- [ ] Edge names match reference table.
- [ ] Dual-write notes present where applicable.

## Cross-File Dependencies
- Depends on: Phases 1–5 patterns and events.
- Blocking: Final validation.

## Next Steps
- [ ] Mark phase complete after edits/validation.
- [ ] Run `validation-checklist.md`.
