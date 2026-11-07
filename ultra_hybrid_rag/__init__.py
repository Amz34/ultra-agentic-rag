"""
Ultra Agentic Hybrid RAG Engine.
Combines Hierarchical Tree Navigation (PageIndex/RAPTOR), Knowledge Graph Linking (GraphRAG),
Adaptive Routing, and Self-Corrective Evaluation (CRAG).
"""

from .models import TreeNode, DocumentTree, GraphEntity, GraphRelation, KnowledgeGraph, RetrievalResult
from .indexer import DocumentTreeIndexer
from .knowledge_graph import KnowledgeGraphMesh
from .router import AdaptiveQueryRouter
from .evaluator import SelfCorrectiveEvaluator
from .engine import UltraHybridRAG

__all__ = [
    "TreeNode",
    "DocumentTree",
    "GraphEntity",
    "GraphRelation",
    "KnowledgeGraph",
    "RetrievalResult",
    "DocumentTreeIndexer",
    "KnowledgeGraphMesh",
    "AdaptiveQueryRouter",
    "SelfCorrectiveEvaluator",
    "UltraHybridRAG",
]
