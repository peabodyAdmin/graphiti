# Phase 3: 02-archtecture.md Updates

## Context
- Update architecture doc to describe edge-based patterns and event-driven binding.

## Edge Type Reference
(full table included for self-containment; same as prior phases)

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

## Edits for 02-archtecture.md
- [ ] ### Edit 3.1: Episode Binding Lifecycle
  - Describe event-driven pattern: Graphiti async creation, subscribe to episode created, then create HAS_CONTENT edge; no name-based polling.
- [ ] ### Edit 3.2: Alternative Cascade Algorithm
  - Rewrite cascade to traverse RESPONDS_TO edges and HAS_ALTERNATIVE, not embedded arrays.
- [ ] ### Edit 3.3: Context Assembly (WorkingMemory)
  - Clarify WorkingMemory is computed via graph traversals (HAS_TURN→HAS_ALTERNATIVE active path, HAS_SUMMARY, HAS_ACTIVE_ENTITY, HAS_CONTENT); no WorkingMemory edges.
- [ ] ### Edit 3.4: Compression & Summarization
  - Use HAS_SUMMARY, SUMMARIZES, HAS_CONTENT, COVERS_UP_TO, CREATED_BY_PROCESS edges for lineage.

## Validation Checklist
- [ ] Episode binding flow shows async HAS_CONTENT edge creation.
- [ ] Cascade algorithm references RESPONDS_TO/HAS_ALTERNATIVE edges.
- [ ] WorkingMemory described as computed traversal only.
- [ ] Compression lineage uses edge terms consistently.
- [ ] Edge names match reference table.

## Cross-File Dependencies
- Depends on: Phases 1–2 (edge definitions and BR alignment).
- Blocking: AsyncAPI/OpenAPI updates rely on these patterns.

## Next Steps
- [ ] Mark phase complete after edits/validation.
- [ ] Proceed to `phase4-endpoint-classification.md`.
