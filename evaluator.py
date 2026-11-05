"""
Self-Corrective Evaluator (Inspired by Corrective RAG / CRAG).
Evaluates retrieved evidence completeness, detects dangling footnotes/tables,
and triggers corrective actions before synthesis.
"""

import re
from typing import List, Dict, Tuple, Any
from .models import TreeNode, DocumentTree


class SelfCorrectiveEvaluator:
    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold

    def evaluate_evidence(
        self,
        query: str,
        retrieved_nodes: List[TreeNode],
        doc_tree: DocumentTree
    ) -> Tuple[float, List[str], List[TreeNode]]:
        """
        Calculates confidence score, detects gaps (e.g. missing footnotes or isolated table cells),
        and applies corrective node expansion.
        """
        corrective_actions: List[str] = []
        expanded_nodes = list(retrieved_nodes)
        
        if not retrieved_nodes:
            return 0.0, ["ZERO_RESULTS: Triggering full tree fallback"], []

        # 1. Check keyword coverage between query and retrieved nodes
        q_words = set(re.findall(r"\b[a-zA-Z0-9_\-\$]{3,}\b", query.lower()))
        combined_text = " ".join([f"{n.title} {n.content} {' '.join(n.keywords)}" for n in retrieved_nodes]).lower()
        
        matches = [w for w in q_words if w in combined_text]
        coverage_ratio = len(matches) / max(len(q_words), 1)
        base_confidence = min(0.5 + (coverage_ratio * 0.5), 1.0)

        # 2. Check for Dangling Footnote / Note References
        # E.g. content mentions "See Note 4" or "[^1]" but Note 4 is not in retrieved_nodes
        footnote_ref_pat = re.compile(r"(?:Note|Footnote)\s*(\d+)|\[\^([a-zA-Z0-9_\-]+)\]", re.I)
        missing_notes = set()

        for node in retrieved_nodes:
            for match in footnote_ref_pat.finditer(node.content):
                note_num = match.group(1) or match.group(2)
                if note_num:
                    missing_notes.add(note_num)

        # Check if missing notes are already present in retrieved_nodes
        present_node_titles = " ".join([n.title for n in retrieved_nodes]).lower()
        for note_identifier in list(missing_notes):
            if f"note {note_identifier}".lower() not in present_node_titles:
                # Corrective action: Locate target note in doc_tree and expand!
                for t_id, t_node in doc_tree.node_map.items():
                    if f"note {note_identifier}".lower() in t_node.title.lower():
                        if t_node not in expanded_nodes:
                            expanded_nodes.append(t_node)
                            corrective_actions.append(
                                f"FOOTNOTE_RECONCILIATION: Automatically ingested Note {note_identifier} ('{t_node.title}')"
                            )
                            base_confidence = min(base_confidence + 0.15, 0.98)

        # 3. Check Parent Node Escalation if node is a sub-table with no context
        for node in retrieved_nodes:
            if node.level > 2 and len(node.content.split()) < 30 and node.parent_id:
                parent = doc_tree.node_map.get(node.parent_id)
                if parent and parent not in expanded_nodes:
                    expanded_nodes.insert(0, parent)
                    corrective_actions.append(
                        f"PARENT_ESCALATION: Ingested parent section '{parent.title}' for context framing"
                    )
                    base_confidence = min(base_confidence + 0.10, 0.98)

        return base_confidence, corrective_actions, expanded_nodes
