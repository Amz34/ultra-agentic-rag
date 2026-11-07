"""
Adaptive Query Router & Intent Classifier.
Determines whether query requires:
1. TREE_PINPOINT (Single page fact, specific section/table lookup)
2. GRAPH_MULTI_HOP (Entity relationships, cross-company/period comparisons)
3. HYBRID_SYNTHESIS (Comprehensive synthesis requiring both tree hierarchy & entity linkages)
"""

import re
from typing import Dict, Any


class AdaptiveQueryRouter:
    def __init__(self):
        self.pinpoint_patterns = [
            re.compile(r"\b(what is the (?:exact )?value of|page number|footnote|table \d+|operating margin in \d{4})\b", re.I),
            re.compile(r"\b(how much|total revenue|ebitda in \d{4}|defined in section)\b", re.I)
        ]
        self.multi_hop_patterns = [
            re.compile(r"\b(compare|difference between|relationship between|impact of .* on .*|how did .* affect)\b", re.I),
            re.compile(r"\b(cross-reference|across all notes|trend from \d{4} to \d{4})\b", re.I)
        ]

    def route_query(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower()

        # Check multi-hop indicators
        for p in self.multi_hop_patterns:
            if p.search(q_lower):
                return {
                    "strategy": "GRAPH_MULTI_HOP",
                    "reason": f"Detected comparative/relational phrasing matching '{p.pattern}'",
                    "needs_graph": True,
                    "needs_tree": True
                }

        # Check pinpoint indicators
        for p in self.pinpoint_patterns:
            if p.search(q_lower):
                return {
                    "strategy": "TREE_PINPOINT",
                    "reason": f"Detected specific structural/metric lookup matching '{p.pattern}'",
                    "needs_graph": False,
                    "needs_tree": True
                }

        # Default to Hybrid Synthesis
        return {
            "strategy": "HYBRID_SYNTHESIS",
            "reason": "General question: combining hierarchical tree navigation with entity linking",
            "needs_graph": True,
            "needs_tree": True
        }
