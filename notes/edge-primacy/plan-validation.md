## Coherence Assessment: Edge-Primacy Migration Plan

### Plan Internal Coherence
**Phase 1**: issues found  
- Edge table introduces both `BOUND_TO_EPISODE` and `HAS_CONTENT` for Summary/Introspection → Episode without a clear split; Edit 1.8 only uses `HAS_CONTENT`, creating an internal collision.  
- Edit 1.3 targets Process template provenance even though Processes have no template reference and the edge table only allows `INSTANTIATED_FROM` for Service/Tool.  
- WorkingMemory is described as computed (no edges) while the initial audit suggested edges; the phase does not reconcile this change in stance.

**Phase 2**: issues found  
- Template BRs (immutability/instantiation) are not mentioned despite `INSTANTIATED_FROM` being in the edge table, leaving template rules property-based.  
- Alternative cascade edits reference `RESPONDS_TO`, but BR-ALT cache-status logic still depends on `isActive` semantics from arrays; the phase does not spell out how to derive it from edges.

**Phase 3**: issues found  
- Episode binding flow assumes an `EpisodeCreated` event but does not note whether `SCOPED_TO` targets Conversation vs User; ambiguity remains from Phase 1.  
- Cascade rewrite relies on `RESPONDS_TO` but keeps `HAS_ALTERNATIVE` sequences as edge properties; ordering semantics are not specified.

**Phase 4**: coherent  
- Single edit aligns classification to edge-creation mutations; no internal contradictions detected.

**Phase 5**: issues found  
- Edge table still contains the Summary/Introspection dual-edge conflict (`BOUND_TO_EPISODE` vs `HAS_CONTENT`).  
- New `AlternativeCreated` event is proposed, but the plan does not reconcile existing `alternative.creation.requested/created` events in the current AsyncAPI (potential duplication).  
- Compression event edit mentions edge intents but omits whether `SCOPED_TO` is emitted for summary Episodes.

**Phase 6**: issues found  
- Relationship endpoints (Edit 6.6) are introduced without counterparts in earlier phases or current docs; unclear whether these are new endpoints or just documentation views.  
- POST endpoint notes (Edit 6.7) rely on knowing which edges are synchronous vs asynchronous, but prior phases only defined this for Episodes; other edges’ timing is unspecified.  
- Metric edges (`FOR_ENTITY`, `OF_METRIC`) appear in the edge table yet no OpenAPI edits cover Metric schemas.

### Cross-Phase Coherence
**Edge Type Consistency**: inconsistencies found  
- `SCOPED_TO` target alternates between Conversation and User; current docs use `group_id = userId`, while Phase 1 tables allow both without choosing.  
- Summary/Introspection edges conflict: some phases expect `HAS_CONTENT`, others also keep `BOUND_TO_EPISODE`.  
- Template provenance edges defined, but only Phase 1 mentions Process templating (not supported elsewhere) and later phases ignore template BRs.

**Dependency Chain**: issues found  
- Phase 5 assumes an `EpisodeCreated` event emitting edge intents that Phase 3/4 do not define; ordering of edge creation vs event emission is underspecified.  
- Phase 6’s new relationship endpoints depend on edge definitions, but earlier phases do not specify how those edges are exposed or versioned.

**Coverage Gaps**: gaps found  
- Metric edges are listed in every edge table but are never addressed in edits (BRs, architecture, AsyncAPI, or OpenAPI).  
- Template edge treatment stops at Phase 1; Business Rules and API/Event specs remain pointer-based for templates.  
- Dual-write strategy is called out, but there is no phase covering how/when properties are actually deprecated or removed.

### Expected Documentation Coherence (Post-Migration)
**Entity Model ↔ Business Rules**: misaligned  
- Ownership/scoping edge model conflicts with BRs that remain property-centric for templates and metrics; ambiguous `SCOPED_TO` target could leave BR-EPISODE-002/BR-ENTITY-008 inconsistent with the model.

**REST API ↔ Event Schemas**: misaligned  
- AsyncAPI introduces edge-intent events (Phase 5) without reconciling existing event names/schemas; OpenAPI (Phase 6) adds relationship endpoints not covered by AsyncAPI.  
- Episode binding edges are async, but REST schemas for alternatives/summaries/introspections still lack clarity on when `BOUND_TO_EPISODE` vs `HAS_CONTENT` is available.

**Architecture ↔ Implementation Specs**: misaligned  
- Architecture (Phase 3) assumes edge-based cascade and binding, but OpenAPI edits (Phase 6) still rely on deprecating properties rather than defining relationship payloads; WorkingMemory is described as computed but earlier audit suggests edges, leaving context assembly story muddled.

### Critical Issues (Must Resolve Before Execution)
1. Summary/Introspection → Episode edge conflict (`BOUND_TO_EPISODE` vs `HAS_CONTENT`): choose a single edge or define distinct semantics; ensure all phases align.  
2. `SCOPED_TO` target ambiguity (Conversation vs User) vs existing `group_id = userId` invariant; decide the canonical target and dual-write rules.  
3. Template provenance scope: remove Process template references or extend edge/table support and update BR-TEMPLATE/OpenAPI/AsyncAPI accordingly.  
4. Metrics: either drop `FOR_ENTITY`/`OF_METRIC` from the edge set or add edits in BRs/architecture/OpenAPI/AsyncAPI to cover them.  
5. Event duplication: Phase 5’s `AlternativeCreated` event must be reconciled with existing AsyncAPI channels to avoid two event shapes for the same action.

### Recommendations
1. Lock an authoritative edge glossary (targets + semantics) before editing—resolve SCOPED_TO and Summary/Introspection edges, and strip unused edges (metrics/template/process).  
2. Add a mini-phase or appendix covering metrics and template edges (BRs + API/Event schemas) or explicitly defer/removal to avoid half-migrated concepts.  
3. Define edge creation timing (sync vs async) per edge type and propagate to Phase 5/6 so POST and events stay in sync.  
4. Clarify WorkingMemory stance (computed only vs persisted edges) and reflect it in Phase 1/3 narratives and in OpenAPI/AsyncAPI responses.  
5. Consolidate alternative events (reuse existing channels with new payloads) to prevent schema divergence.

### Overall Assessment
Needs revision — core edge semantics (scoping, content binding, template/metric coverage, and event alignment) are unsettled; proceeding would propagate inconsistencies across all six docs.
