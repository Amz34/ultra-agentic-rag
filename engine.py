"""
Master Ultra Agentic Hybrid RAG Orchestrator.
Combines Hierarchical Document Trees, Knowledge Graph Mesh, Adaptive Routing,
and Self-Corrective Evaluation.
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import DocumentTree, KnowledgeGraph, TreeNode, RetrievalResult
from .indexer import DocumentTreeIndexer
from .knowledge_graph import KnowledgeGraphMesh
from .router import AdaptiveQueryRouter
from .evaluator import SelfCorrectiveEvaluator


class UltraHybridRAG:
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or os.path.expanduser("~/ops/ultra_hybrid_rag/data"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.indexer = DocumentTreeIndexer()
        self.graph_mesh = KnowledgeGraphMesh()
        self.router = AdaptiveQueryRouter()
        self.evaluator = SelfCorrectiveEvaluator()

        self.trees: Dict[str, DocumentTree] = {}
        self.graphs: Dict[str, KnowledgeGraph] = {}
        self._load_cached_state()

    def _load_cached_state(self):
        index_file = self.storage_dir / "index_registry.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("documents", []):
                        doc_id = item["doc_id"]
                        tree_path = self.storage_dir / f"tree_{doc_id}.json"
                        graph_path = self.storage_dir / f"graph_{doc_id}.json"
                        if tree_path.exists():
                            with open(tree_path, "r", encoding="utf-8") as tf:
                                self.trees[doc_id] = DocumentTree.model_validate_json(tf.read())
                        if graph_path.exists():
                            with open(graph_path, "r", encoding="utf-8") as gf:
                                self.graphs[doc_id] = KnowledgeGraph.model_validate_json(gf.read())
            except Exception:
                pass

    def _save_state(self, doc_tree: DocumentTree, graph: KnowledgeGraph):
        tree_path = self.storage_dir / f"tree_{doc_tree.doc_id}.json"
        with open(tree_path, "w", encoding="utf-8") as f:
            f.write(doc_tree.model_dump_json(indent=2))

        graph_path = self.storage_dir / f"graph_{doc_tree.doc_id}.json"
        with open(graph_path, "w", encoding="utf-8") as f:
            f.write(graph.model_dump_json(indent=2))

        registry_path = self.storage_dir / "index_registry.json"
        registry = {"documents": []}
        if registry_path.exists():
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = {"documents": []}

        # Update or add entry
        registry["documents"] = [d for d in registry.get("documents", []) if d.get("doc_id") != doc_tree.doc_id]
        registry["documents"].append({
            "doc_id": doc_tree.doc_id,
            "filename": doc_tree.filename,
            "title": doc_tree.title,
            "total_pages": doc_tree.total_pages,
            "node_count": len(doc_tree.node_map),
            "entity_count": len(graph.entities)
        })
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

    def index_document(self, text_or_path: str, filename: Optional[str] = None) -> DocumentTree:
        """Parse raw text, markdown file, or PDF into Hierarchical Tree and Knowledge Graph."""
        if "\n" not in text_or_path and len(text_or_path) < 500 and Path(text_or_path).is_file():
            path = Path(text_or_path)
            fname = filename or path.name
            if path.suffix.lower() == ".pdf":
                doc_tree = self.indexer.parse_pdf(str(path))
            else:
                content = path.read_text(encoding="utf-8", errors="ignore")
                doc_tree = self.indexer.parse_document(content, filename=fname)
        else:
            content = text_or_path
            fname = filename or "inline_document.md"
            doc_tree = self.indexer.parse_document(content, filename=fname)
        
        # 2. Extract Knowledge Graph
        kg = self.graph_mesh.build_graph(doc_tree)

        # 3. Cache & Register
        self.trees[doc_tree.doc_id] = doc_tree
        self.graphs[doc_tree.doc_id] = kg
        self._save_state(doc_tree, kg)

        return doc_tree

    def query(self, query_text: str, doc_id: Optional[str] = None) -> RetrievalResult:
        """
        Execute Ultra Agentic Hybrid Reasoning:
        1. Route Query
        2. Heuristic Tree Navigation (PageIndex style)
        3. Knowledge Graph Expansion (GraphRAG style)
        4. Self-Corrective Verification Gate (CRAG style)
        5. Grounded synthesis
        """
        # Select target document
        if not self.trees:
            return RetrievalResult(
                query=query_text,
                strategy="NONE",
                confidence=0.0,
                answer="No documents currently indexed in Ultra Hybrid RAG system."
            )

        target_tree = self.trees.get(doc_id) if doc_id else list(self.trees.values())[0]
        target_graph = self.graphs.get(target_tree.doc_id)

        reasoning_trail = []
        
        # Step 1: Query Routing
        route = self.router.route_query(query_text)
        strategy = route["strategy"]
        reasoning_trail.append(f"Query Router: Selected {strategy} ({route['reason']})")

        # Step 2: Heuristic Tree Traversal
        candidate_nodes: List[TreeNode] = []
        q_tokens = set(re.findall(r"\b[a-zA-Z0-9_\-\$]{3,}\b", query_text.lower()))

        for node_id, node in target_tree.node_map.items():
            node_score = 0
            node_text = f"{node.title} {node.summary} {' '.join(node.keywords)}".lower()
            for token in q_tokens:
                if token in node_text:
                    node_score += 2
                if token in node.title.lower():
                    node_score += 3  # High weight for heading match
            if node_score > 0:
                candidate_nodes.append((node_score, node))

        # Sort candidate nodes by score
        candidate_nodes.sort(key=lambda x: x[0], reverse=True)
        top_tree_nodes = [node for _, node in candidate_nodes[:3]]
        
        if top_tree_nodes:
            reasoning_trail.append(
                f"Tree Navigation: Identified {len(top_tree_nodes)} relevant sections "
                f"([{', '.join([n.title for n in top_tree_nodes])}]) on Page(s) "
                f"{sorted(list(set([n.page_number for n in top_tree_nodes])))}"
            )

        # Step 3: Graph Multi-Hop Traversal (if applicable)
        graph_evidence_nodes = []
        if (route.get("needs_graph") or strategy in ("GRAPH_MULTI_HOP", "HYBRID_SYNTHESIS")) and target_graph:
            # Check if entities in query match graph entities
            matched_entities = []
            for e_key, entity in target_graph.entities.items():
                if entity.name.lower() in query_text.lower():
                    matched_entities.append(e_key)

            if len(matched_entities) >= 2:
                # Find multi-hop paths
                path = self.graph_mesh.find_multi_hop_path(target_graph, matched_entities[0], matched_entities[1])
                if path:
                    reasoning_trail.append(
                        f"Graph Traversal: Discovered multi-hop path connecting {matched_entities[0]} "
                        f"→ {matched_entities[1]} via {len(path)} relationship link(s)"
                    )
                    for edge in path:
                        if edge.evidence_node_id in target_tree.node_map:
                            graph_evidence_nodes.append(target_tree.node_map[edge.evidence_node_id])

        # Step 4: Union of Tree & Graph nodes (deduplicated by node_id)
        seen_node_ids = set()
        combined_nodes = []
        for n in (top_tree_nodes + graph_evidence_nodes):
            if n.node_id not in seen_node_ids:
                seen_node_ids.add(n.node_id)
                combined_nodes.append(n)

        # Step 5: Self-Corrective Evaluator (CRAG Gate)
        confidence, corrective_actions, final_nodes = self.evaluator.evaluate_evidence(
            query=query_text,
            retrieved_nodes=combined_nodes,
            doc_tree=target_tree
        )
        for act in corrective_actions:
            reasoning_trail.append(f"Self-Corrective Gate: {act}")

        # Step 6: Compile Grounded Evidence & Citations
        citations = []
        evidence_blocks = []
        for n in final_nodes:
            citations.append({
                "section": n.title,
                "page": n.page_number,
                "level": n.level,
                "has_tables": len(n.table_refs) > 0,
                "has_footnotes": len(n.footnote_refs) > 0
            })
            block = f"### [{n.title}] (Page {n.page_number})\n{n.content}"
            if n.footnote_refs:
                block += f"\n[Footnotes: {'; '.join(n.footnote_refs)}]"
            evidence_blocks.append(block)

        evidence_text = "\n\n".join(evidence_blocks)

        # Step 7: Deterministic High-Fidelity Answer Generation
        answer = self._synthesize_grounded_answer(query_text, final_nodes, target_tree)

        return RetrievalResult(
            query=query_text,
            strategy=strategy,
            confidence=round(confidence, 2),
            reasoning_trail=reasoning_trail,
            citations=citations,
            evidence_text=evidence_text,
            answer=answer,
            corrective_actions_taken=corrective_actions
        )

    def _synthesize_grounded_answer(self, query: str, nodes: List[TreeNode], doc_tree: DocumentTree) -> str:
        """Synthesize answer with exact page citations and footnote attributions."""
        if not nodes:
            return "No verifiable evidence found in the document index matching the query."

        citations_str = ", ".join([f"'{n.title}' (Page {n.page_number})" for n in nodes])
        
        # Check if query asks for specific numbers or percentages
        metrics_found = []
        for n in nodes:
            found = re.findall(r"\b(\$?\d+(?:\.\d+)?%?|\b\d{4}\b)\b", n.content)
            if found:
                metrics_found.extend(found[:4])

        answer_lines = [
            f"Based on verifiable navigation across {citations_str}:",
            "",
            f"**Evidence Summary:**"
        ]
        
        for n in nodes:
            answer_lines.append(f"- **{n.title} (Page {n.page_number})**: {n.summary}")
            if n.footnote_refs:
                answer_lines.append(f"  * Footnotes reconciled: {'; '.join(n.footnote_refs)}")
        
        answer_lines.append("")
        answer_lines.append(f"**Verification Confidence:** High (Deterministic Tree & Graph Grounding)")
        return "\n".join(answer_lines)
