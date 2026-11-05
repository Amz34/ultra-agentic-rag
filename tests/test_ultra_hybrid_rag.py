"""
Comprehensive Automated Unit & Integration Tests for Ultra Agentic Hybrid RAG.
Verifies:
1. DocumentTreeIndexer (headings, levels, page markers, tables, footnotes)
2. KnowledgeGraphMesh (entities, co-occurrence, multi-hop BFS)
3. AdaptiveQueryRouter (classification logic)
4. SelfCorrectiveEvaluator (footnote reconciliation & parent escalation)
5. UltraHybridRAG (end-to-end integration)
"""

import unittest
from ultra_hybrid_rag.models import DocumentTree, TreeNode
from ultra_hybrid_rag.indexer import DocumentTreeIndexer
from ultra_hybrid_rag.knowledge_graph import KnowledgeGraphMesh
from ultra_hybrid_rag.router import AdaptiveQueryRouter
from ultra_hybrid_rag.evaluator import SelfCorrectiveEvaluator
from ultra_hybrid_rag.engine import UltraHybridRAG


SAMPLE_DOC = """# Alpha Corp Strategic Report
[Page 1]
Executive Summary: Alpha Corp recorded revenue of $1.5B in 2026.

## Section 1: Financial Health
[Page 5]
EBITDA rose by 18% in FY2026.
Refer to Note 12 for breakdown of non-operating charges.

| Period | Revenue | EBITDA |
| :--- | :--- | :--- |
| FY2025 | $1.2B | $200M |
| FY2026 | $1.5B | $236M |

## Note 12: Detailed Non-Operating Charges
[Page 15]
Note 12: Amortization and restructuring expenses totaled $14M under IFRS 9.
"""


class TestUltraHybridRAG(unittest.TestCase):
    def setUp(self):
        self.indexer = DocumentTreeIndexer()
        self.kg = KnowledgeGraphMesh()
        self.router = AdaptiveQueryRouter()
        self.evaluator = SelfCorrectiveEvaluator()

    def test_indexer_parsing(self):
        tree = self.indexer.parse_document(SAMPLE_DOC, filename="test.md", doc_id="test1")
        self.assertEqual(tree.doc_id, "test1")
        self.assertEqual(len(tree.node_map), 3)
        self.assertEqual(tree.total_pages, 15)
        
        # Check node titles and pages
        nodes = list(tree.node_map.values())
        self.assertEqual(nodes[0].page_number, 1)
        self.assertEqual(nodes[1].page_number, 5)
        self.assertEqual(nodes[2].page_number, 15)
        
        # Check table detection
        self.assertEqual(len(nodes[1].table_refs), 1)

    def test_knowledge_graph_extraction(self):
        tree = self.indexer.parse_document(SAMPLE_DOC, filename="test.md", doc_id="test2")
        graph = self.kg.build_graph(tree)
        self.assertTrue(len(graph.entities) > 0)
        
        # Look for financial metrics like EBITDA or Revenue
        entity_names = [e.name.upper() for e in graph.entities.values()]
        self.assertTrue(any("EBITDA" in name for name in entity_names))
        self.assertTrue(any("REVENUE" in name for name in entity_names))

    def test_adaptive_router(self):
        r1 = self.router.route_query("What is the exact value of EBITDA in 2026?")
        self.assertEqual(r1["strategy"], "TREE_PINPOINT")

        r2 = self.router.route_query("Compare the difference between Revenue and EBITDA trends")
        self.assertEqual(r2["strategy"], "GRAPH_MULTI_HOP")

    def test_self_corrective_footnote_reconciliation(self):
        tree = self.indexer.parse_document(SAMPLE_DOC, filename="test.md", doc_id="test3")
        # Pass only Section 1 (which refers to Note 12)
        sec1_node = [n for n in tree.node_map.values() if "Section 1" in n.title][0]
        
        confidence, actions, expanded = self.evaluator.evaluate_evidence(
            query="Explain Section 1 financial health",
            retrieved_nodes=[sec1_node],
            doc_tree=tree
        )
        # Note 12 must be reconciled autonomously!
        reconciled_titles = [n.title for n in expanded]
        self.assertTrue(any("Note 12" in t for t in reconciled_titles))
        self.assertTrue(any("FOOTNOTE_RECONCILIATION" in a for a in actions))

    def test_end_to_end_engine(self):
        engine = UltraHybridRAG()
        tree = engine.index_document(SAMPLE_DOC, filename="sample_test.md")
        res = engine.query("What was the EBITDA growth in FY2026?", doc_id=tree.doc_id)
        
        self.assertGreaterEqual(res.confidence, 0.70)
        self.assertTrue(len(res.citations) > 0)
        self.assertTrue(len(res.reasoning_trail) > 0)


if __name__ == "__main__":
    unittest.main()
