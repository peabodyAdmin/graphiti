## Coherence Assessment: Edge-Primacy Migration Plan

### Plan Internal Coherence
**Phase 1**: coherent  
- Edge table aligns to 19-edge set; WorkingMemory marked computed-only; HAS_CONTENT-only binding; timing table present (HAS_CONTENT/SUMMARIZES async).

**Phase 2**: minor note  
- BR-ALT still implies `isActive` array semantics; consider a sentence on deriving cache status via RESPONDS_TO + active flag, but otherwise edge references align.

**Phase 3**: coherent  
- Episode binding uses HAS_CONTENT async; WorkingMemory traversal references HAS_CONTENT; cascade references RESPONDS_TO/HAS_ALTERNATIVE.

**Phase 4**: coherent  
- Classification matches edge-creation mutations; no contradictions.

**Phase 5**: coherent  
- Alternative events extend existing alternative.* channels with edge intents (no duplication); HAS_CONTENT-only binding noted.

**Phase 6**: minor note  
- Relationship endpoints called out; acceptable as doc-first addition but ensure API surface matches future implementation.

### Cross-Phase Coherence
**Edge Type Consistency**: consistent  
- All phases use the 19-edge set (HAS_CONTENT binding; no templates/metrics/SCOPED_TO).

**Dependency Chain**: valid  
- Phases build sequentially; async binding relies on HAS_CONTENT after Graphiti ingestion as noted in Phase 3/5.

**Coverage Gaps**: minor  
- Dual-write/deprecation timing (e.g., group_id, legacy id fields) is not scheduled; add a cleanup note if needed.

### Expected Documentation Coherence (Post-Migration)
**Entity Model ↔ Business Rules**: aligned with minor note  
- Ownership via edges; scoping remains property-only (group_id). Ensure BR-ALT cache-status wording references RESPONDS_TO + active flag.

**REST API ↔ Event Schemas**: mostly aligned  
- Alternative event shape resolved (extend existing channels). HAS_CONTENT async binding is noted; ensure OpenAPI response notes when binding is available.

**Architecture ↔ Implementation Specs**: aligned with minor follow-up  
- Architecture’s edge-based cascade/binding matches AsyncAPI; OpenAPI still needs explicit relationship payloads and timing notes (sync vs async) per edge.

### Critical Issues (Must Resolve Before Execution)
None blocking. Optional tighten-ups: clarify BR-ALT cache derivation via edges; document relationship endpoint availability/timing in Phase 6; add a deprecation/cleanup step for legacy properties.

### Recommendations
1. Keep the 19-edge glossary handy in each phase; ensure OpenAPI responses note when HAS_CONTENT bindings appear (post-async).  
2. Add a short note on deprecating legacy id properties once edges are live (esp. group_id dual-write stance).  
3. Add one line in Phase 2 to tie BR-ALT cache status to RESPONDS_TO + active flag if further clarity is needed.

### Overall Assessment
Ready to execute — core edge set and scoping decisions are aligned; only minor clarifications remain optional.
