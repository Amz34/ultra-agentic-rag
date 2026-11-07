"""
Ultra Agentic Hybrid RAG Engine.
Combines Hierarchical Tree Navigation (PageIndex/RAPTOR), Knowledge Graph Linking (GraphRAG),
Adaptive Routing, and Self-Corrective Evaluation (CRAG).
"""
try:
    from .ultra_hybrid_rag import *
except (ImportError, ValueError):
    from ultra_hybrid_rag import *
