# Validation Checklist (Post-Phases)

Use this after completing all six phase files.

## Cross-File Consistency
- [ ] Edge type names consistent across all docs (match reference table).
- [ ] Dual-write notes present for deprecated properties awaiting removal.
- [ ] All deprecated properties marked and replacement edges given.
- [ ] WorkingMemory consistently described as computed (no edges).
- [ ] Secret vault pattern consistent (no credentials in graph).

## Edge Primacy
- [ ] All property pointers replaced with edge relationships (one location only).
- [ ] Embedded alternative arrays deprecated in favor of nodes.
- [ ] Episode/Entity scoping uses group_id property (no edge).
- [ ] Summary/introspection lineage uses edges (HAS_SUMMARY, SUMMARIZES, HAS_CONTENT, COVERS_UP_TO, CREATED_BY_PROCESS).
- [ ] ProcessStep dependencies use CALLS_TOOL/CALLS_PROCESS/DEPENDS_ON.

## Event/API Alignment
- [ ] AsyncAPI events describe edge intents (not ids).
- [ ] OpenAPI POST endpoints document which edges are created and when (sync vs async).
- [ ] Endpoint classification reflects edge-based mutations.

## Progress Tracking
- [ ] All phase edit checkboxes marked.
- [ ] Phase completion boxes in README updated.
- [ ] This validation checklist completed.
