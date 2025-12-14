# Edge Migration Audit Report (prior to phased update)

## Executive Summary
- Found pervasive property-as-pointer usage across all six docs; highest density in `00-foundation.md` and `05-openapi.md`.
- Core relationships (ownership, provenance, execution bindings, tree structure, entity membership) are encoded as `<thing>Id` properties instead of edges.
- Most anti-patterns cluster around Conversations/Turns/Alternatives, Tool/Service/Secret chains, and Graphiti artifacts (Episodes, Entities, Summaries) tied back by IDs.
- High confidence that ownership, provenance, dependency, and tree structure should be edges; medium confidence for Graphiti-managed `group_id` and WorkingMemory arrays; low confidence for metrics dimensions that may remain denormalized.

## Findings by Document

### 00-foundation.md
#### Finding 1: Ownership via `ownerId`/`userId`
**Current State:**
- Properties: `ownerId` on Service/Tool/Process/ServiceTemplate/ToolTemplate; `userId` on Secret/Conversation; `group_id` on Episode/Entity for scoping.
**Proposed Change:**
- Remove ownership/scoping properties; add edges: `(Resource)-[:OWNED_BY]->(User)` and `(Episode|Entity)-[:SCOPED_TO]->(Conversation|User)`.
- Edge properties: `created_at` (optionally on edge), `shared` can remain node property.
**Impact:**
- API schemas drop `ownerId`/`userId` outputs; sharing/visibility checks become graph traversals.
- Business rules BR-SHARE/BR-SEC align to edge existence instead of property equality.
- Queries shift to `MATCH (r)-[:OWNED_BY]->(u {id:$user})`.
**Migration Notes:** Backfill edges from stored properties; maintain `shared` property for discovery filters.

#### Finding 2: Template provenance (`serviceTemplateId`/`toolTemplateId`)
**Current State:**
- Properties: `serviceTemplateId`, `toolTemplateId` soft references on instances.
**Proposed Change:**
- Add edges: `(Service)-[:INSTANTIATED_FROM {at: timestamp}]->(ServiceTemplate)`, `(Tool)-[:INSTANTIATED_FROM]->(ToolTemplate)`.
- Keep provenance even if template archived.
**Impact:** Event payloads and APIs carry template edge creation instead of storing UUIDs; BR-TEMPLATE references check edge presence.
**Migration Notes:** Create edges from existing IDs; preserve archived template info as edge property or node flag.

#### Finding 3: Tool dependency chain (`serviceId`, `secretId`)
**Current State:**
- Properties: `serviceId` on Tool; `connectionParams.secretId`; Service requiresSecret drives validation.
**Proposed Change:**
- Edges: `(Tool)-[:USES_SERVICE]->(Service)`, `(Tool)-[:USES_SECRET]->(Secret)` (conditional).
- Edge properties: `connectionParams` values (non-secret) or auth metadata.
**Impact:** Runtime validation (BR-SHARE-007/BR-SECRET-002B) becomes edge checks; OpenAPI/AsyncAPI shift from ids to edge creation intents.
**Migration Notes:** Rehydrate edges from stored IDs; decide how to store secret material off-graph while keeping the edge.

#### Finding 4: ProcessStep links (`toolId`/`processId`/`dependsOn`)
**Current State:**
- Properties inside ProcessStep: `toolId` or `processId` (exclusive), `dependsOn` array of step IDs.
**Proposed Change:**
- Represent steps as nodes: `(ProcessStep)-[:CALLS_TOOL]->(Tool)` or `[:CALLS_PROCESS]->(Process)`; `[:DEPENDS_ON]->` between steps; `[:OUTPUTS]->(Variable)` optional.
**Impact:** BR-PROCESS-* validation uses graph structure; execution scheduling traverses dependencies instead of parsing arrays.
**Migration Notes:** Promote steps to nodes or explicit relationships; ensure recursion depth tracked via edges.

#### Finding 5: Conversation structure (`processId`, `parentConversationId`, `forkOrigin*`, `activeEntities`)
**Current State:**
- Properties: `processId` (UI hint), `parentConversationId`, `forkOriginTurnId`, `forkOriginAlternativeId`, `activeEntities` list of entity UUIDs.
**Proposed Change:**
- Edges: `(Conversation)-[:DEFAULT_PROCESS]->(Process)` (mutable); `(Conversation)-[:FORKED_FROM]->(Conversation)` with properties `originTurn`, `originAlternative`; `(Conversation)-[:HAS_ACTIVE_ENTITY {addedAt}]->(Entity)`.
**Impact:** Fork provenance and active entity membership become traversals; BR-CONV-003/004 enforced via edges.
**Migration Notes:** Fork edges need properties for origin refs; active entities edge state replaces arrays.

#### Finding 6: Turn/Alternative tree and Episode binding (`conversationId`, `parentTurnId`, `inputContext.parentAlternativeId`, `processId`, `episodeId`)
**Current State:**
- Turn has `conversationId` and `parentTurnId` properties; Alternative has `inputContext.parentAlternativeId`, `processId`, `episodeId` properties.
**Proposed Change:**
- Model Alternatives as nodes: `(Turn)-[:HAS_ALTERNATIVE]->(Alternative)`; `(Alternative)-[:BELONGS_TO]->(Turn)`; `(Turn)-[:CHILD_OF {viaAlternative}]->(Turn)`; `(Alternative)-[:RESPONDS_TO]->(Alternative)` (parent alt); `(Alternative)-[:EXECUTED_BY]->(Process)`; `(Alternative)-[:BOUND_TO_EPISODE]->(Episode)`.
**Impact:** BR-ALT cascade becomes relationship traversal; Episode binding ceases to be string backfill; cache validity derived by comparing edges.
**Migration Notes:** Requires schema shift (alternative nodes); backfill from existing arrays; keep `isActive` as property or edge state.

#### Finding 7: Episode scoping via `group_id`
**Current State:**
- Graphiti Episodes store `group_id` = conversationId; treated as property pointer.
**Proposed Change:**
- Edge: `(Episode)-[:SCOPED_TO]->(Conversation)` (or User). Maintain `group_id` only if Graphiti requires.
**Impact:** Semantic search and context assembly can traverse scope edges; dedup honors graph scope.
**Migration Notes:** Coordinate with Graphiti core; may need dual-write property + edge for compatibility.

#### Finding 8: WorkingMemory references (`conversationId`, `currentTurnId`, `currentAlternativeId`, `immediatePath[]`, `summaries`, `activeEntities`, `introspectionContext`)
**Current State:**
- WorkingMemory stores multiple ID arrays.
**Proposed Change:**
- Edges: `(WorkingMemory)-[:FOR_CONVERSATION]->(Conversation)`; `(WorkingMemory)-[:FOCUSED_AT]->(Alternative)`; `(WorkingMemory)-[:IMMEDIATE_PATH {order}]->(Alternative)`; `(WorkingMemory)-[:USES_SUMMARY]->(Summary)`; `(WorkingMemory)-[:INCLUDES_ENTITY]->(Entity)`; `(WorkingMemory)-[:INCLUDES_INTROSPECTION]->(Episode)`.
**Impact:** Token accounting and path rebuilds become graph traversals; BR-MEMORY-* reference edge cardinality.
**Migration Notes:** WorkingMemory may remain computed/cache node; ensure edges rebuilt on updates.

#### Finding 9: Entity provenance (`group_id`, `sources[].created_by/episode_id`, `enriched_by`)
**Current State:**
- Properties: `group_id`, `sources` embedded with `created_by`, `episode_id`, `original_name`, `confidence`; `enriched_by` processId.
**Proposed Change:**
- Edges: `(Entity)-[:MENTIONED_IN {sourceType,confidence,original_name}]->(Episode)`; `(Entity)-[:CREATED_BY]->(User)`; `(Entity)-[:ENRICHED_BY {at}]->(Process)`; `(Entity)-[:SCOPED_TO]->(Conversation|User)`.
**Impact:** Dedup and enrichment use edges; BR-ENTITY-* enforced via graph.
**Migration Notes:** Map existing `sources` array to multiple edges; keep facet/enrichment data as properties.

#### Finding 10: Summary/Introspection pointers (`conversationId`, `episodeId`, `sourceEpisodeIds`, `priorTurnId`, `createdBy`, `episodeId` on introspection)
**Current State:**
- Properties link Summary to Conversation, source Episodes, content Episode, prior Turn, creating Process; Introspection holds Episode pointer.
**Proposed Change:**
- Edges: `(Conversation)-[:HAS_SUMMARY]->(Summary)`; `(Summary)-[:HAS_CONTENT]->(Episode)`; `(Summary)-[:SUMMARIZES]->(Episode)` (multiple, ordered) with `compressionLevel`; `(Summary)-[:CREATED_BY]->(Process)`; `(Summary)-[:COVERS_UP_TO]->(Turn)`; `(Introspection)-[:HAS_CONTENT]->(Episode)`; `(Introspection)-[:SCOPED_TO]->(User|Conversation)`.
**Impact:** Compression lineage and introspection carousel become traversable; BR-SUMMARY-* validations rely on relationships.
**Migration Notes:** Backfill edges from arrays; keep `compressionLevel` as property.

#### Finding 11: Metrics pointers (`metricId`, `entityId`, `dimensions.userId/conversationId`)
**Current State:**
- MetricValue stores `metricId` and `entityId` strings plus dimensions map.
**Proposed Change:**
- Edges: `(MetricValue)-[:OF_METRIC]->(MetricDefinition)`; `(MetricValue)-[:FOR_ENTITY]->(Service|Tool|Process|Conversation)`; optional `(MetricValue)-[:FOR_USER]->(User)` for scoped attribution.
**Impact:** Analytics queries become graph traversals; retention rules target edges.
**Migration Notes:** Could keep dimensions as properties for ad-hoc filtering; edges add semantic clarity.

### 01-business_rules.md
#### Finding 1: Sharing/ownership checks via properties (`ownerId`, `shared`)
**Current State:** Rules compare `ownerId`/`shared` properties to authorize usage across Service/Tool/Secret/Process/Conversation.
**Proposed Change:** Move to edges `[:OWNED_BY]` and `[:VISIBILITY {shared:true}]` or derive sharing from a `[:SHARED_WITH]->(User|Group)` edge.
**Impact:** BR-SHARE-* validations become graph queries; conflict detection uses edge presence.
**Migration Notes:** Introduce visibility edges; keep `shared` boolean as cached flag if needed.

#### Finding 2: Cross-user validation sequences using ID equality (`Conversation.userId != Tool.ownerId`, etc.)
**Current State:** Rules BR-SHARE-007/EXEC-003 rely on comparing IDs.
**Proposed Change:** Validate traversals: ensure `(Conversation)-[:OWNED_BY]->(User)` and `(Tool)-[:OWNED_BY]->(User)` align or `(Tool)-[:SHARED_WITH]->(User)` exists.
**Impact:** Runtime validation walks edges; clearer audit trail of sharing scope.
**Migration Notes:** Migration requires constructing `SHARED_WITH` edges or a `SHARED` node.

#### Finding 3: Alternative cascade references (`parentAlternativeId`, `inputContext` IDs)
**Current State:** BR-ALT-* enforces correctness via properties.
**Proposed Change:** Use edges `(Alternative)-[:RESPONDS_TO]->(Alternative)` and `(Turn)-[:CHILD_OF {viaAlternative}]->(Turn)`; cascade walks edges.
**Impact:** Staleness and activation derived from relationship graph instead of stored ids.
**Migration Notes:** Requires alternative nodes; cacheStatus derivation becomes traversal.

#### Finding 4: WorkingMemory and token budgets referencing IDs
**Current State:** BR-MEMORY-* uses arrays of IDs to validate path and scope.
**Proposed Change:** Validate via edges linking WorkingMemory to alternatives/summaries/entities.
**Impact:** Budget checks and cross-conversation guards use graph structure.
**Migration Notes:** Recompute edges whenever WorkingMemory updates.

### 02-archtecture.md
#### Finding 1: Template and dependency references (`templateId`, `serviceId`, `toolId`, `conversationId`)
**Current State:** Event flows and validation discuss IDs, not edges.
**Proposed Change:** Workers create/validate edges (`INSTANTIATED_FROM`, `USES_SERVICE`, `HAS_TURN`).
**Impact:** Health checks and dependency validation traverse edges rather than comparing ids.
**Migration Notes:** Update worker inputs to reference nodes or edge creation instructions.

#### Finding 2: Context assembly uses `group_id`, `activeEntities` arrays
**Current State:** Context builder collects IDs from properties.
**Proposed Change:** Traverse `(Conversation)-[:HAS_TURN]->(Turn)-[:HAS_ALTERNATIVE]->(Alternative)-[:BOUND_TO_EPISODE]->(Episode)` and `(Conversation)-[:HAS_ACTIVE_ENTITY]->(Entity)` to build context.
**Impact:** Reduces duplication and stale caches; enables richer graph queries.
**Migration Notes:** Requires entity edges and alternative nodes.

#### Finding 3: Process selection hint via `conversation.processId`
**Current State:** UI hint stored as property.
**Proposed Change:** Edge `(Conversation)-[:DEFAULT_PROCESS]->(Process)` with mutable target.
**Impact:** Hint updates are relationship rewires; analytics can see history of preferences via edge timeline.
**Migration Notes:** Optional to keep property for backward compatibility.

### 03-endpoint-classification.md
#### Finding 1: Request payloads/path params carry IDs (`serviceId`, `toolId`, `processId`, etc.)
**Current State:** API classification assumes pointer properties for associations.
**Proposed Change:** Mutation endpoints should express relationship creation (edges) rather than embedding IDs; e.g., POST Tool accepts target Service node ref to create `USES_SERVICE` edge.
**Impact:** Classification unchanged, but schemas must shift away from pointer properties.
**Migration Notes:** Requires OpenAPI adjustments and client updates.

### 04-async-api.md
#### Finding 1: Event payloads encode relationships as IDs
**Current State:** Messages like `ToolCreationRequested` carry `serviceId`, `toolTemplateId`, `secretId`.
**Proposed Change:** Events should describe edge creations (`usesService`, `usesSecret`, `instantiatedFromTemplate`) instead of raw IDs.
**Impact:** Downstream workers form edges directly; failure events reference relationship types.
**Migration Notes:** Version AsyncAPI schemas; keep IDs temporarily for compatibility.

#### Finding 2: Alternative/Turn events use `conversationId`, `parentTurnId`, `parentAlternativeId`
**Current State:** Tree structure encoded as properties in events.
**Proposed Change:** Events emit relationships: `HAS_TURN`, `CHILD_OF`, `RESPONDS_TO`.
**Impact:** Tree reconstruction uses event-driven edge creation; simplifies cascade logic.
**Migration Notes:** Update event consumers to create edges on receipt.

#### Finding 3: Context compression/introspection events carry `conversationId`, `sourceEpisodeIds`
**Current State:** Provenance embedded as arrays.
**Proposed Change:** Events should trigger edges `(Summary)-[:SUMMARIZES]->(Episode)` and `(Introspection)-[:SCOPED_TO]->(User|Conversation)`.
**Impact:** Lineage tracking becomes first-class graph structure.
**Migration Notes:** Align with Summary/Introspection schema changes.

### 05-openapi.md
#### Finding 1: Core schemas rely on pointer properties (`serviceId`, `toolId`, `processId`, `conversationId`, `parentTurnId`, `parentAlternativeId`, `episodeId`)
**Current State:** Request/response bodies encode relationships as string IDs.
**Proposed Change:** Redesign schemas to express relationships as edges (e.g., ToolCreate body names target Service node; TurnCreate expresses parent link via edge creation).
**Impact:** Major OpenAPI change; client/server DTOs change; BR references update to relationship constraints.
**Migration Notes:** Consider vNext API or compatibility shims that translate IDs to edges server-side.

#### Finding 2: WorkingMemory/ConversationTree schemas embed arrays of IDs
**Current State:** `immediatePath`, `activeEntities`, `relationships[]` in ConversationTree are property lists.
**Proposed Change:** Represent paths as edges; APIs return graph fragments (nodes + typed relationships) instead of ID arrays.
**Impact:** UI consumes graph structure directly; simplifies cache status derivation.
**Migration Notes:** Provide transitional responses with both structures.

#### Finding 3: Summary/Introspection schemas use ID properties for provenance
**Current State:** `episodeId`, `sourceEpisodeIds`, `priorTurnId`, `createdBy` in Summary; `episodeId`, `position` in Introspection.
**Proposed Change:** Use edges `HAS_CONTENT`, `SUMMARIZES`, `COVERS_UP_TO`, `CREATED_BY_PROCESS`, `SCOPED_TO`.
**Impact:** Compression lineage and carousel positioning become relational data.
**Migration Notes:** Add relationship payloads; keep position as property.

#### Finding 4: Metrics schemas (`metricId`, `entityId`, `dimensions.userId/conversationId`)
**Current State:** IDs in MetricValue.
**Proposed Change:** Edge-based associations for metric attribution; dimensions become edge properties or remain as tags.
**Impact:** Enables graph analytics on metrics.
**Migration Notes:** Provide dual representation during transition.

## Summary of Proposed Edge Types
| Edge Type | From | To | Properties | Replaces Property |
|-----------|------|----|------------|-------------------|
| OWNED_BY | Service/Tool/Process/Template/Secret/Conversation | User | created_at | ownerId/userId |
| INSTANTIATED_FROM | Service/Tool | ServiceTemplate/ToolTemplate | at | serviceTemplateId/toolTemplateId |
| USES_SERVICE | Tool | Service | connectionParams sans secrets | serviceId |
| USES_SECRET | Tool | Secret | scope metadata | connectionParams.secretId |
| DEFAULT_PROCESS | Conversation | Process | since | processId (hint) |
| FORKED_FROM | Conversation | Conversation | originTurn, originAlternative | parentConversationId/forkOrigin* |
| HAS_TURN | Conversation | Turn | sequence | conversationId |
| CHILD_OF | Turn | Turn | viaAlternative | parentTurnId |
| HAS_ALTERNATIVE | Turn | Alternative | isActive | embedded alternatives |
| RESPONDS_TO | Alternative | Alternative | none | inputContext.parentAlternativeId |
| EXECUTED_BY | Alternative | Process | createdAt | alternative.processId |
| BOUND_TO_EPISODE | Alternative/Summary/Introspection | Episode | source, createdAt | episodeId |
| SUMMARIZES | Summary | Episode | order | sourceEpisodeIds |
| HAS_ACTIVE_ENTITY | Conversation/WorkingMemory | Entity | addedAt, relevance | activeEntities |
| SCOPED_TO | Episode/Entity | Conversation/User | none | group_id |
| CALLS_TOOL/CALLS_PROCESS | ProcessStep | Tool/Process | timeout, interactionMode | toolId/processId |
| DEPENDS_ON | ProcessStep | ProcessStep | order | dependsOn |
| FOR_ENTITY | MetricValue | Service/Tool/Process/Conversation | dimensions | entityId |
| OF_METRIC | MetricValue | MetricDefinition | none | metricId |

## Questions & Concerns
### Architectural Questions
1. Do we control Graphiti core enough to add `SCOPED_TO` edges for Episodes/Entities, or do we need dual-write of `group_id` + edges?
2. Should Alternatives become first-class nodes, or do we keep embedded documents and mirror edges in a separate projection?
3. How should secrets be modeled safely as edges without leaking credentials—edge with opaque secret ref plus off-graph vault?

### Performance Considerations
- Relationship-heavy model needs relationship indexes on `OWNED_BY`, `USES_SERVICE`, `CHILD_OF`, `RESPONDS_TO`, `BOUND_TO_EPISODE`.
- WorkingMemory rebuilds via traversals may outperform array manipulation but need caching for deep trees.
- MetricValue high-volume writes may justify keeping dimension properties as tags even if edges exist.

### Backward Compatibility
- May require API vNext or translation layer: accept IDs, immediately create edges, and phase out properties.
- Migration scripts to backfill edges from existing properties (`*_id` fields) before dropping properties.
- Event schemas need versioning; consumers must understand both ID and edge-intent payloads during rollout.

## Confidence Levels
**High Confidence:** Ownership edges; Tool→Service/Secret; Conversation/Turn/Alternative/Episode edges; Template provenance; Summary lineage; ProcessStep dependencies.

**Medium Confidence:** Episode/Entity `group_id` replacement; WorkingMemory path edges; activeEntities edges; DEFAULT_PROCESS hint edge.

**Low Confidence:** MetricValue dimension edges; Worker currentJob edges (operational detail may remain properties).

## Recommended Implementation Order
1. Phase 1: Ownership/provenance edges; Tool dependency edges; Conversation↔Turn↔Alternative↔Episode edges (core graph integrity).
2. Phase 2: Summary/introspection lineage edges; ProcessStep dependency edges; DEFAULT_PROCESS and FORKED_FROM edges; active entity edges.
3. Phase 3: WorkingMemory path edges; Graphiti `group_id` dual-write; MetricValue attribution edges; event/OpenAPI schema updates.

## Next Steps
- Decide on Alternative node promotion and Graphiti dual-write strategy.
- Draft migration plan (backfill edges, API compatibility layer).
- Update OpenAPI/AsyncAPI to express relationships as edge creations; adjust workers to enforce via graph traversals.
