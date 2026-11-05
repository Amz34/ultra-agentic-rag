"""
Knowledge Graph Mesh (Inspired by Microsoft GraphRAG and Cognee).
Extracts named entities, domain concepts, and relational edges across document nodes.
"""

import re
from typing import Dict, List, Set, Tuple
from .models import DocumentTree, GraphEntity, GraphRelation, KnowledgeGraph


class KnowledgeGraphMesh:
    def __init__(self):
        # Entity detection heuristics
        self.entity_patterns = {
            "FINANCIAL_METRIC": re.compile(
                r"\b(EBITDA|Operating Cash Flow|Net Income|Free Cash Flow|Revenue|Gross Margin|Capex|OpEx|ARR|MRR|EPS)\b",
                re.IGNORECASE
            ),
            "REGULATION": re.compile(
                r"\b(IFRS\s*\d+|GAAP|SEC\s*Form\s*10-K|GDPR|HIPAA|ISO\s*\d+|SOX)\b",
                re.IGNORECASE
            ),
            "YEAR_DATE": re.compile(r"\b(20[1-3][0-9]|FY\d{2,4}|Q[1-4]\s*20\d{2})\b"),
            "ORGANIZATION": re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\s+(?:Inc|Corp|LLC|Ltd|Technologies|Holdings|Group|AI)))\b")
        }

    def build_graph(self, doc_tree: DocumentTree) -> KnowledgeGraph:
        entities: Dict[str, GraphEntity] = {}
        relations: List[GraphRelation] = []

        # 1. Extract entities per node
        node_entities: Dict[str, Set[str]] = {}

        for node_id, node in doc_tree.node_map.items():
            full_text = f"{node.title}\n{node.content}"
            node_entities[node_id] = set()

            for etype, pattern in self.entity_patterns.items():
                matches = pattern.findall(full_text)
                for match in matches:
                    ename = match.strip() if isinstance(match, str) else match[0].strip()
                    if len(ename) < 2:
                        continue
                    
                    key = f"{ename.upper()}_{etype}"
                    if key not in entities:
                        entities[key] = GraphEntity(
                            name=ename,
                            entity_type=etype,
                            mentions=[node_id]
                        )
                    else:
                        if node_id not in entities[key].mentions:
                            entities[key].mentions.append(node_id)
                    
                    node_entities[node_id].add(key)

        # 2. Extract co-occurrence & cross-reference relationships
        seen_edges: Set[Tuple[str, str, str]] = set()

        # Connect entities co-occurring in the same node
        for node_id, ent_keys in node_entities.items():
            ent_list = sorted(list(ent_keys))
            for i in range(len(ent_list)):
                for j in range(i + 1, len(ent_list)):
                    src = ent_list[i]
                    tgt = ent_list[j]
                    edge_key = (src, tgt, "CO_OCCURS_IN")
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        relations.append(GraphRelation(
                            source=src,
                            target=tgt,
                            relation="CO_OCCURS_IN",
                            evidence_node_id=node_id,
                            weight=1.0
                        ))

        # Explicit cross-reference links (e.g. "Refer to Note 4" or "See Appendix B")
        cross_ref_pat = re.compile(r"(?:refer to|see|in accordance with|as disclosed in)\s+(Note\s*\d+|Section\s*[A-Z0-9\.]+|Appendix\s*[A-Z0-9]+)", re.IGNORECASE)
        for node_id, node in doc_tree.node_map.items():
            refs = cross_ref_pat.findall(node.content)
            for ref in refs:
                ref_clean = ref.strip().upper()
                for target_id, target_node in doc_tree.node_map.items():
                    if ref_clean in target_node.title.upper():
                        edge_key = (node_id, target_id, "CROSS_REFERENCES")
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            relations.append(GraphRelation(
                                source=node_id,
                                target=target_id,
                                relation="CROSS_REFERENCES",
                                evidence_node_id=node_id,
                                weight=2.0
                            ))

        return KnowledgeGraph(entities=entities, relations=relations)

    def find_multi_hop_path(self, graph: KnowledgeGraph, entity_a: str, entity_b: str, max_depth: int = 3) -> List[GraphRelation]:
        """Breadth-first search for multi-hop relationship paths."""
        adj: Dict[str, List[GraphRelation]] = {}
        for r in graph.relations:
            adj.setdefault(r.source, []).append(r)
            # Bidirectional co-occurrence
            if r.relation == "CO_OCCURS_IN":
                adj.setdefault(r.target, []).append(GraphRelation(
                    source=r.target,
                    target=r.source,
                    relation=r.relation,
                    evidence_node_id=r.evidence_node_id,
                    weight=r.weight
                ))

        queue: List[List[GraphRelation]] = [[]]
        visited = {entity_a}

        while queue:
            path = queue.pop(0)
            curr = entity_a if not path else path[-1].target
            if curr == entity_b and path:
                return path

            if len(path) >= max_depth:
                continue

            for edge in adj.get(curr, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append(path + [edge])

        return []
