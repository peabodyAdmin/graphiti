# Edge Migration: Architectural Decisions & Implementation Plan

## Architectural Decisions

### Question 1: Graphiti SCOPED_TO Edges — ANSWERED
**Decision:** Dual-write `group_id` + `SCOPED_TO` edge for Episodes/Entities.  
**Rationale:** Graphiti core requires `group_id`; semantic traversal needs edges.  
**Implementation:** Always set `group_id` when calling Graphiti APIs; when the Episode/Entity exists, `MERGE (episode)-[:SCOPED_TO {created_at: datetime()}]->(conversation)`.  
**Monitoring:** Validate `group_id` matches `SCOPED_TO` target (see consistency check in Long-Term Strategy).

### Question 2: Alternatives as First-Class Nodes — ANSWERED
**Decision:** Promote Alternatives to nodes.  
**Rationale:** Required to express `RESPONDS_TO`, `EXECUTED_BY`, `BOUND_TO_EPISODE`; enables cascade traversal.  
**Edge design:** Only `HAS_ALTERNATIVE` from Turn → Alternative (bidirectional traversal), plus `RESPONDS_TO`, `EXECUTED_BY`, `BOUND_TO_EPISODE`.

### Question 3: Secret Modeling — ANSWERED
**Decision:** Secrets hold metadata + opaque vault reference; Tool↔Secret via `USES_SECRET` edge.  
**Rationale:** Prevent credential exposure; edge carries semantics, vault holds value.  
**Runtime:** Verify `(secret)-[:OWNED_BY]->(user)` then fetch via vault key.

### Question 4: WorkingMemory Edges — ANSWERED
**Decision:** WorkingMemory is computed, not persisted as edges.  
**Rationale:** It is an ephemeral view per request/turn; duplicating edges adds churn.  
**Implementation:** Traverse existing edges (`HAS_ACTIVE_ENTITY`, `HAS_TURN`→`HAS_ALTERNATIVE`, `HAS_SUMMARY`) to assemble context on demand.

### Question 5: Long-Term Graphiti Strategy — ANSWERED
**Decision:** Maintain dual-write (`group_id` + `SCOPED_TO` edge) indefinitely unless upstream adds edge support.  
**Trade-off:** Slight redundancy for upstream compatibility.  
**Consistency check:**  
```python
async def validate_graphiti_scope_consistency():
    inconsistent = await cypher_read("""
        MATCH (e:Episode)-[:SCOPED_TO]->(target)
        WHERE e.group_id <> target.id
        RETURN e.id as episode_id, e.group_id as property_target, target.id as edge_target
    """)
    if inconsistent:
        raise ValidationError(f"Inconsistent group_id vs SCOPED_TO: {len(inconsistent)} rows")
```

## Index Strategy

Create indexes before any backfill:
```cypher
// Ownership & provenance
CREATE INDEX owned_by_created_at IF NOT EXISTS FOR ()-[r:OWNED_BY]->() ON (r.created_at);
CREATE INDEX instantiated_from_timestamp IF NOT EXISTS FOR ()-[r:INSTANTIATED_FROM]->() ON (r.at);

// Conversation structure
CREATE INDEX has_turn_sequence IF NOT EXISTS FOR ()-[r:HAS_TURN]->() ON (r.sequence);
CREATE INDEX child_of_alternative IF NOT EXISTS FOR ()-[r:CHILD_OF]->() ON (r.viaAlternative);
CREATE INDEX has_alternative_active IF NOT EXISTS FOR ()-[r:HAS_ALTERNATIVE]->() ON (r.isActive);
CREATE INDEX has_alternative_sequence IF NOT EXISTS FOR ()-[r:HAS_ALTERNATIVE]->() ON (r.sequence);

// Episode binding & scoping
CREATE INDEX bound_to_episode_created IF NOT EXISTS FOR ()-[r:BOUND_TO_EPISODE]->() ON (r.createdAt);
CREATE INDEX scoped_to_index IF NOT EXISTS FOR ()-[r:SCOPED_TO]->();

// Tool dependencies
CREATE INDEX uses_service_index IF NOT EXISTS FOR ()-[r:USES_SERVICE]->();
CREATE INDEX uses_secret_scope IF NOT EXISTS FOR ()-[r:USES_SECRET]->() ON (r.scope);

// Summary & compression
CREATE INDEX summarizes_order IF NOT EXISTS FOR ()-[r:SUMMARIZES]->() ON (r.order);

// Process execution
CREATE INDEX executed_by_created IF NOT EXISTS FOR ()-[r:EXECUTED_BY]->() ON (r.createdAt);
CREATE INDEX depends_on_order IF NOT EXISTS FOR ()-[r:DEPENDS_ON]->() ON (r.order);

// Active entities
CREATE INDEX has_active_entity_added IF NOT EXISTS FOR ()-[r:HAS_ACTIVE_ENTITY]->() ON (r.addedAt);
CREATE INDEX has_active_entity_relevance IF NOT EXISTS FOR ()-[r:HAS_ACTIVE_ENTITY]->() ON (r.relevance);
```

Verify core node indexes exist (id on all primary node labels, `group_id` on Episode).

## Constraint Strategy

Establish constraints (Neo4j 5+ supports relationship property constraints):
```cypher
// Uniqueness
CREATE CONSTRAINT unique_conversation_id IF NOT EXISTS FOR (n:Conversation) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT unique_turn_id IF NOT EXISTS FOR (n:Turn) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT unique_alternative_id IF NOT EXISTS FOR (n:Alternative) REQUIRE n.id IS UNIQUE;
// ...repeat for User, Service, Tool, Process, Secret, Summary, Introspection, Episode, Entity...

// Relationship property requirements
CREATE CONSTRAINT owned_by_has_timestamp IF NOT EXISTS FOR ()-[r:OWNED_BY]->() REQUIRE r.created_at IS NOT NULL;
CREATE CONSTRAINT has_turn_sequence_required IF NOT EXISTS FOR ()-[r:HAS_TURN]->() REQUIRE r.sequence IS NOT NULL;
CREATE CONSTRAINT has_alternative_sequence_required IF NOT EXISTS FOR ()-[r:HAS_ALTERNATIVE]->() REQUIRE r.sequence IS NOT NULL;
CREATE CONSTRAINT has_alternative_active_required IF NOT EXISTS FOR ()-[r:HAS_ALTERNATIVE]->() REQUIRE r.isActive IS NOT NULL;
```

If node-existence constraints are available in your Neo4j version, add: Tool requires Service (`(t:Tool)-[:USES_SERVICE]->(:Service)`), Alternative requires Turn (`(:Turn)-[:HAS_ALTERNATIVE]->(a:Alternative)`), Episode must be scoped (`(:Episode)-[:SCOPED_TO]->()`).

## Implementation Plan

### Global Prerequisites
- Index creation script applied and verified.
- Constraints created and verified.
- Database backup taken.
- Feature flags configured (edge usage, dual-write).
- Monitoring and alerting in place.

### Phase 1: Core Graph Integrity
**Prerequisites:** Global prerequisites complete.  
**Completion Criteria:** Ownership/provenance/dependency edges exist for all new writes; legacy data backfilled; validators use edges (with property fallback); dual-write enabled for rollback.

#### 1.1 Ownership Edges
**Prerequisites:** None.  
**Completion Criteria:** `OWNED_BY` edges for Service, Tool, Process, ServiceTemplate, ToolTemplate, Secret, Conversation; creation endpoints emit edges; backfill complete; BR-SHARE uses edge traversal.
**Tasks:**
- Define `OWNED_BY` edge schema.
- Update creation endpoints immediately to create `OWNED_BY`.
- Keep `ownerId/userId` properties temporarily (dual-write).
- Backfill existing nodes using idempotent, batched pattern.
- Add validation and tests for ownership/sharing using edges with property fallback.

#### 1.2 Template Provenance
**Prerequisites:** 1.1 complete.  
**Completion Criteria:** `INSTANTIATED_FROM` edges for Service→ServiceTemplate and Tool→ToolTemplate; creation paths dual-write; backfill done.
**Tasks:** Update creation workers/endpoints to create provenance edges; backfill with idempotent pattern; tests for provenance queries and archival behavior.

#### 1.3 Tool Dependency Chain
**Prerequisites:** 1.2 complete.  
**Completion Criteria:** `USES_SERVICE` and `USES_SECRET` edges created on new Tools; vault reference pattern in place; backfill complete; BR-SHARE/BR-SECRET enforce via edges.
**Tasks:** Update Tool creation to emit dependency edges; dual-write `serviceId/secretId` for rollback; backfill; tests for access checks and secret scoping.

#### 1.4 Conversation → Turn Structure
**Prerequisites:** 1.3 complete.  
**Completion Criteria:** `HAS_TURN` and `CHILD_OF` edges created on new Turns; backfill complete; fork provenance maintained.
**Tasks:** Update Turn creation to create structural edges; dual-write `conversationId/parentTurnId`; backfill; tests for tree traversal and fork origin tracking.

### Phase 2: Alternative Nodes & Semantic Lineage
**Prerequisites:** Phase 1 complete.  
**Completion Criteria:** Alternatives as nodes with full lineage; episode binding event-driven; summary/introspection lineage captured; process dependency graph established.

#### 2.1 Alternative Node Promotion
**Prerequisites:** Phase 1 complete.  
**Completion Criteria:** All alternatives migrated to nodes; `HAS_ALTERNATIVE`, `RESPONDS_TO`, `EXECUTED_BY` edges in place; cascade uses edge traversal; deprecated arrays retained only for rollback.
**Tasks:** Define Alternative schema; migration from embedded arrays to nodes using idempotent batches; update alternative creation API; update cascade algorithm to traverse `RESPONDS_TO`; tests for navigation/cascade/activation; verify 100% migration.

#### 2.2 Episode Binding Edges (Event-Driven)
**Prerequisites:** 2.1 complete.  
**Completion Criteria:** `BOUND_TO_EPISODE` and `SCOPED_TO` edges created via event-driven flow; backfill complete; no race conditions.
**Critical Pattern (Graphiti async):**
```python
async def create_alternative_with_episode(turn_id, content, conversation_id, sequence=0):
    alt_id = generate_id()
    await cypher_write("""
        MATCH (t:Turn {id: $turn_id})
        CREATE (a:Alternative {id: $alt_id, isActive: true, createdAt: datetime()})
        MERGE (t)-[:HAS_ALTERNATIVE {sequence: $sequence, isActive: true}]->(a)
    """, {"turn_id": turn_id, "alt_id": alt_id, "sequence": sequence})

    episode_name = f"Alternative {alt_id}"
    await graphiti.add_memory(
        name=episode_name,
        episode_body=content,
        group_id=conversation_id,
        source="message"
    )

    await event_bus.subscribe(
        channel="graphiti.episodes.created",
        handler=on_episode_created,
        filter={"name": episode_name, "group_id": conversation_id}
    )
    return alt_id

async def on_episode_created(event):
    episode_id = event["episode_id"]
    conversation_id = event["group_id"]
    episode_name = event["name"]
    alt_id = episode_name.split(" ")[-1]  # name convention carries alt id

    await cypher_write("""
        MATCH (e:Episode {id: $episode_id})
        MATCH (c:Conversation {id: $conversation_id})
        MATCH (a:Alternative {id: $alt_id})
        MERGE (e)-[:SCOPED_TO {created_at: datetime()}]->(c)
        MERGE (a)-[:BOUND_TO_EPISODE {createdAt: datetime()}]->(e)
    """, {"episode_id": episode_id, "conversation_id": conversation_id, "alt_id": alt_id})
```
**Tasks:** Implement event-driven binding; dual-write `group_id`; backfill binding edges from stored `episodeId`; add retry/timeout for missing events; tests for binding, scope traversal, cache staleness detection.

#### 2.3 Summary & Introspection Lineage
**Prerequisites:** 2.2 complete.  
**Completion Criteria:** `HAS_SUMMARY`, `SUMMARIZES`, `HAS_CONTENT`, `COVERS_UP_TO`, `CREATED_BY_PROCESS`, `SCOPED_TO` edges in place; backfill complete; traversal-based provenance works.
**Tasks:** Add edges on compression/introspection; backfill from properties/arrays; tests for compression lineage and carousel navigation.

#### 2.4 Process Dependencies
**Prerequisites:** 2.3 complete.  
**Completion Criteria:** ProcessSteps modeled with `CALLS_TOOL` / `CALLS_PROCESS` / `DEPENDS_ON`; execution orchestrator traverses graph; backfill complete.
**Tasks:** Promote steps to nodes or explicit relationships; update execution to traverse dependency graph; backfill from `toolId/processId/dependsOn`; tests for scheduling, cycle detection, recursion limits.

### Phase 3: Context & Analytics
**Prerequisites:** Phase 2 complete.  
**Completion Criteria:** Context-related edges in place; WorkingMemory computed via traversal; metrics attribution edges established.

#### 3.1 Active Entity Edges
**Prerequisites:** None beyond Phase 2.  
**Completion Criteria:** `HAS_ACTIVE_ENTITY` edges replace arrays; backfill complete; context assembly uses edges.
**Tasks:** Update activation flows to create/remove edges; dual-write optional; backfill; tests for membership and relevance.

#### 3.2 Fork Provenance
**Prerequisites:** 3.1 complete.  
**Completion Criteria:** `FORKED_FROM` edges with `originTurn`, `originAlternative`; backfill complete.
**Tasks:** Update fork creation to emit edge; backfill from `parentConversationId/forkOrigin*`; tests for lineage queries.

#### 3.3 Default Process Hint
**Prerequisites:** 3.2 complete.  
**Completion Criteria:** `DEFAULT_PROCESS` edge used for UI hint; backfill complete; hint updates rewire edge.
**Tasks:** Update preference updates to rewrite edge; dual-write `processId` for rollback; tests for preference changes.

#### 3.4 WorkingMemory Computation
**Prerequisites:** 3.1–3.3 complete (source edges exist).  
**Completion Criteria:** `build_working_memory()` traverses edges; no WorkingMemory edges created; performance validated.
**Tasks:** Implement computed builder (no persisted edges); update context assembly and token accounting; tests for path reconstruction and budgets; perf target: traversal completion within acceptable baseline (see Performance Tests).

#### 3.5 Metrics Attribution
**Prerequisites:** 3.4 complete.  
**Completion Criteria:** `OF_METRIC` and `FOR_ENTITY` edges on MetricValues; backfill complete; queries use edges.
**Tasks:** Update metric writes to create attribution edges; decide on dimension properties vs edges; backfill; tests for analytics and retention.

### Phase 4: Schema Finalization & Documentation
**Prerequisites:** Phases 1–3 complete; edge-based APIs live; grace period for dual-write elapsed.  
**Completion Criteria:** Pointer properties removed; docs/specs updated; performance optimized.

#### 4.1 Property Deprecation
**Prerequisites:** Dual-write not needed (properties unused).  
**Completion Criteria:** `*Id` properties and embedded arrays removed; DB cleaned; indexes updated to edge-focused.
**Tasks:** Drop legacy properties/arrays; remove property indexes; verify no queries rely on them.

#### 4.2 OpenAPI/AsyncAPI Documentation
**Prerequisites:** 4.1 complete.  
**Completion Criteria:** Specs reflect edge-based model; ID-based fields removed; migration guide published.
**Tasks:** Update OpenAPI/AsyncAPI to edge-intent schemas; document relationship constraints and errors; refresh examples/Cypher.

#### 4.3 Performance Optimization
**Prerequisites:** 4.1 complete.  
**Completion Criteria:** Edge queries meet performance goals; indexes verified; caching in place where needed.
**Tasks:** Profile traversals; add/verify relationship indexes; optimize WorkingMemory builder; benchmark vs property baseline.

## Migration Strategy

### Backfill Pattern (Production Grade)
- **Idempotent:** Use `MERGE`; safe to rerun.
- **Resumable:** Checkpoint file tracks offsets per node type.
- **Batched:** Process limited batches to avoid timeouts.
- **Atomic per batch:** All-or-nothing within a batch.
- **Validated:** Post-migration orphan check.

Use this pattern for every backfill (ownership, provenance, dependencies, alternatives, bindings, lineage, metrics).

## Rollback Procedures

### General Pattern
1. Disable feature flag to stop forward progress.
2. Ensure legacy properties still populated (dual-write safety).
3. Remove problematic edges created during the phase (scoped by timestamp).
4. Validate system using property-based logic.
5. Document incident and root cause; plan retry.

### Example: Phase 1.1 Ownership
- Disable `USE_EDGES_FOR_OWNERSHIP`.
- Verify `ownerId/userId` properties exist; restore from backup if missing.
- Delete `OWNED_BY` edges created after migration start if they are incorrect.
- Run ownership/sharing tests using properties.

### Example: Phase 2.1 Alternatives
- Disable `USE_ALTERNATIVE_NODES`.
- Confirm `Turn.alternatives` arrays still present (dual-write kept them).
- Delete Alternative nodes created during migration window.
- Run conversation/alternative flows against legacy structure.

Add similar rollback notes per phase before execution.

## Summary of Proposed Edge Types
| Edge Type | From | To | Properties | Replaces Property |
|-----------|------|----|------------|-------------------|
| OWNED_BY | Service/Tool/Process/Template/Secret/Conversation | User | created_at | ownerId/userId |
| INSTANTIATED_FROM | Service/Tool | ServiceTemplate/ToolTemplate | at | serviceTemplateId/toolTemplateId |
| USES_SERVICE | Tool | Service | connectionParams sans secrets | serviceId |
| USES_SECRET | Tool | Secret | scope | secretId |
| DEFAULT_PROCESS | Conversation | Process | since | processId |
| FORKED_FROM | Conversation | Conversation | originTurn, originAlternative | parentConversationId/forkOrigin* |
| HAS_TURN | Conversation | Turn | sequence | conversationId |
| CHILD_OF | Turn | Turn | viaAlternative | parentTurnId |
| HAS_ALTERNATIVE | Turn | Alternative | isActive, sequence | embedded alternatives |
| RESPONDS_TO | Alternative | Alternative | none | inputContext.parentAlternativeId |
| EXECUTED_BY | Alternative | Process | createdAt | alternative.processId |
| BOUND_TO_EPISODE | Alternative/Summary/Introspection | Episode | source, createdAt | episodeId |
| SUMMARIZES | Summary | Episode | order | sourceEpisodeIds |
| HAS_SUMMARY | Conversation | Summary | none | conversationId |
| HAS_CONTENT | Summary/Introspection | Episode | none | episodeId |
| COVERS_UP_TO | Summary | Turn | none | priorTurnId |
| CREATED_BY_PROCESS | Summary | Process | none | createdBy |
| HAS_ACTIVE_ENTITY | Conversation | Entity | addedAt, relevance | activeEntities |
| SCOPED_TO | Episode/Entity | Conversation/User | none | group_id |
| CALLS_TOOL | ProcessStep | Tool | timeout, interactionMode | toolId |
| CALLS_PROCESS | ProcessStep | Process | timeout | processId |
| DEPENDS_ON | ProcessStep | ProcessStep | order | dependsOn |
| FOR_ENTITY | MetricValue | Service/Tool/Process/Conversation | dimensions | entityId |
| OF_METRIC | MetricValue | MetricDefinition | none | metricId |

## WorkingMemory Computation
- No WorkingMemory edges.
- `build_working_memory(conversation_id)` traverses `HAS_ACTIVE_ENTITY`, `HAS_TURN`→`HAS_ALTERNATIVE` (active), `HAS_SUMMARY`, `BOUND_TO_EPISODE`.
- Token accounting computed from traversed nodes; target runtime: within 2x property-based baseline.

## Performance Tests (Baseline Comparison)
```python
async def test_edge_traversal_performance():
    # Build conversation tree
    conv = await create_conversation()
    turns = []
    for i in range(100):
        parent_alt = turns[-1]["alt"] if turns else None
        turn = await create_turn(conversation=conv, parent_alternative=parent_alt)
        alt = await create_alternative(turn=turn)
        turns.append({"turn": turn, "alt": alt})

    # Baseline: property-based
    baseline_query = """
        MATCH (t:Turn) WHERE t.conversationId = $conv_id RETURN count(t) AS turn_count
    """
    t0 = time.time()
    baseline = await cypher_read(baseline_query, {"conv_id": conv.id})
    baseline_ms = (time.time() - t0) * 1000

    # Edge-based
    edge_query = """
        MATCH (:Conversation {id: $conv_id})-[:HAS_TURN]->(t:Turn) RETURN count(t) AS turn_count
    """
    t1 = time.time()
    edge = await cypher_read(edge_query, {"conv_id": conv.id})
    edge_ms = (time.time() - t1) * 1000

    assert baseline[0]["turn_count"] == edge[0]["turn_count"] == 100
    assert edge_ms < baseline_ms * 2  # within 2x baseline

    indexes = await cypher_read("SHOW INDEXES")
    assert any(idx["name"] == "has_turn_sequence" for idx in indexes), "Missing HAS_TURN index"
```

## Long-Term Strategy
- Keep dual-write for Graphiti `group_id` until upstream supports edges.
- Maintain feature flags for each major edge adoption to allow controlled rollout/rollback.
- Run consistency checks (ownership edges, scope edges) in health monitors.

## Success Metrics
- Data integrity: 100% pointer properties have edge equivalents; orphan checks clean.
- Performance: Edge queries within 2x property baseline; ideally faster with indexes.
- Coverage: Tests cover edge creation, traversal, backfill, rollback paths.
- Compatibility: Legacy clients function via translation layer during dual-write.
- Observability: Events and logs capture edge creation, backfill progress, and failures.
