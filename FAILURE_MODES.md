# System Failure Modes & Operational Safeguards

This document catalogs known systemic edge cases, failure boundaries, and automated mitigation mechanisms within `ultra-agentic-rag`.

---

## 1. Failure Modes Matrix

| Failure Mode | Root Cause | System Behavior | Detection Metric | Automated Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **Malformed Footnote Reference** | Document text contains ambiguous citations (e.g., `Note 4a` vs `Note 4` or non-standard notation). | Evaluator attempts reconciliation; fails to resolve unique node. | `corrective_actions_taken` does not contain target node. | Fallback to parent AST section retrieval with warning logged in reasoning trail. |
| **Unstructured Document Ingestion** | Input document lacks markdown headings (`#`) or page delimiters. | Ingestion engine flattens input into a single root node. | `tree.node_map` length == 1. | Ingestion warning; router automatically routes to Full-Document Summary mode rather than precision pinpoint. |
| **Circular Entity Reference in KG** | Cross-referencing cyclical notes (e.g., Note A references Note B, Note B references Note A). | Graph BFS traversal risks infinite loop. | Traversal depth limit trigger. | BFS visitor set tracks visited entities; hard depth bound at `max_hops=3`. |
| **Context Window Saturation** | Ingestion of dense 200+ page filings with high tabular density. | Multi-hop expansion exceeds LLM prompt budget. | Token budget estimator > threshold. | Rank-based context truncation prioritizing directly cited tables over parent descriptive prose. |

---

## 2. Hard Boundaries & Constraints

1. **Max Graph Traversal Depth**: 3 hops. Deeper relational chains require explicit multi-stage decomposition.
2. **Page Marker Syntax**: Expects `[Page X]` or standard markdown heading delineations for discrete page tracking.
3. **Minimum Confidence Threshold**: Answers below 0.70 confidence trigger an ungrounded warning flag in output payloads.
