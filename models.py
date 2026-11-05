"""
Data models for Ultra Agentic Hybrid RAG Engine.
Synthesizes Hierarchical Tree Indexing (PageIndex), Knowledge Graph Mesh (GraphRAG),
and Self-Corrective Evaluator (CRAG).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TreeNode(BaseModel):
    node_id: str
    title: str
    level: int  # 1 for H1, 2 for H2, etc.
    page_number: int = 1
    summary: str = ""
    content: str = ""
    parent_id: Optional[str] = None
    children: List["TreeNode"] = Field(default_factory=list)
    table_refs: List[str] = Field(default_factory=list)
    footnote_refs: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class DocumentTree(BaseModel):
    doc_id: str
    filename: str
    title: str
    total_pages: int = 1
    root_nodes: List[TreeNode] = Field(default_factory=list)
    node_map: Dict[str, TreeNode] = Field(default_factory=dict)


class GraphEntity(BaseModel):
    name: str
    entity_type: str  # e.g., 'COMPANY', 'FINANCIAL_METRIC', 'LEGAL_CLAUSE', 'DATE', 'PERSON'
    mentions: List[str] = Field(default_factory=list)  # list of node_ids where mentioned


class GraphRelation(BaseModel):
    source: str
    target: str
    relation: str
    evidence_node_id: str
    weight: float = 1.0


class KnowledgeGraph(BaseModel):
    entities: Dict[str, GraphEntity] = Field(default_factory=dict)
    relations: List[GraphRelation] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    query: str
    strategy: str  # 'TREE_PINPOINT', 'GRAPH_MULTI_HOP', 'HYBRID_SYNTHESIS'
    confidence: float
    reasoning_trail: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_text: str = ""
    answer: str = ""
    corrective_actions_taken: List[str] = Field(default_factory=list)
