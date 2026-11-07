"""
Hierarchical Document Tree Indexer (Inspired by VectifyAI/PageIndex and RAPTOR).
Converts structured files into navigation trees preserving sections, tables, footnotes, and page numbers.
"""

import re
import uuid
from typing import List, Dict, Tuple
from .models import TreeNode, DocumentTree


class DocumentTreeIndexer:
    def __init__(self):
        # Heading regex for markdown headers and formal document numbering
        self.header_pattern = re.compile(
            r"^(#{1,6}\s+(.+)|(?:SECTION|PART|NOTE|ITEM)\s+([0-9A-Z\.]+[:\s].+))",
            re.IGNORECASE | re.MULTILINE
        )
        self.page_break_pattern = re.compile(r"(?:<!--\s*page\s*(\d+)\s*-->|\[Page\s*(\d+)\])", re.IGNORECASE)
        self.table_pattern = re.compile(r"(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n*)+)")
        self.footnote_pattern = re.compile(r"(\[\^([a-zA-Z0-9_\-]+)\]:\s*([^\n]+)|(?:Note|Footnote)\s*(\d+)[:\-]\s*([^\n]+))", re.IGNORECASE)

    def parse_pdf(self, pdf_path: str, doc_id: str = None) -> DocumentTree:
        """Extract text with explicit page anchors and outline hierarchy from PDF."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("pypdf is required for PDF parsing. Install with `pip install pypdf`.")

        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pages_text = []

        for idx, page in enumerate(reader.pages):
            p_num = idx + 1
            extracted = page.extract_text() or ""
            pages_text.append(f"\n[Page {p_num}]\n{extracted}")

        combined_text = "\n".join(pages_text)
        from pathlib import Path
        filename = Path(pdf_path).name
        tree = self.parse_document(combined_text, filename=filename, doc_id=doc_id)
        tree.total_pages = max(total_pages, tree.total_pages)
        return tree

    def parse_document(self, text: str, filename: str = "document.md", doc_id: str = None) -> DocumentTree:
        if not doc_id:
            doc_id = str(uuid.uuid4())[:8]

        lines = text.splitlines()
        current_page = 1
        
        # Split document into heading sections
        sections: List[Dict] = []
        current_title = "Document Overview"
        current_level = 1
        current_lines = []
        current_start_page = 1

        for line in lines:
            # Check for page markers
            page_match = self.page_break_pattern.search(line)
            if page_match:
                p_num = page_match.group(1) or page_match.group(2)
                if p_num:
                    current_page = int(p_num)
                    # If this is the start of current section, update start page
                    if not current_lines:
                        current_start_page = current_page

            # Check for heading
            h_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            # Formal headings (e.g. "ITEM 7. MD&A" or "SECTION 1: Title") - must be short header-like lines
            formal_match = re.match(r"^(SECTION|PART|ITEM)\s+([0-9A-Z\.]+[:\s].+)$", line, re.IGNORECASE)
            is_formal_header = formal_match and len(line.strip()) < 80 and not line.strip().endswith(".")
            
            if h_match:
                # Save previous section
                if current_lines or sections:
                    sections.append({
                        "title": current_title.strip(),
                        "level": current_level,
                        "content": "\n".join(current_lines).strip(),
                        "page": current_start_page
                    })
                    current_lines = []
                current_level = len(h_match.group(1))
                current_title = h_match.group(2).strip()
                current_start_page = current_page
            elif is_formal_header:
                if current_lines or sections:
                    sections.append({
                        "title": current_title.strip(),
                        "level": current_level,
                        "content": "\n".join(current_lines).strip(),
                        "page": current_start_page
                    })
                    current_lines = []
                current_level = 2
                current_title = f"{formal_match.group(1).upper()} {formal_match.group(2).strip()}"
                current_start_page = current_page
            else:
                current_lines.append(line)

        # Append last section
        if current_lines:
            sections.append({
                "title": current_title.strip(),
                "level": current_level,
                "content": "\n".join(current_lines).strip(),
                "page": current_start_page
            })

        # Build Hierarchical Tree
        node_map: Dict[str, TreeNode] = {}
        root_nodes: List[TreeNode] = []
        stack: List[TreeNode] = []

        for idx, sec in enumerate(sections):
            content_str = sec["content"]
            
            # Extract tables & footnotes
            tables = [t.strip() for t in self.table_pattern.findall(content_str)]
            footnotes = []
            for fn in self.footnote_pattern.findall(content_str):
                matched_fn = fn[0].strip() if fn[0] else ""
                if matched_fn:
                    footnotes.append(matched_fn)

            # Extract basic keywords & summary
            summary = self._generate_extractive_summary(sec["title"], content_str)
            keywords = self._extract_keywords(sec["title"], content_str)

            node_id = f"node_{idx+1}_{doc_id}"
            tree_node = TreeNode(
                node_id=node_id,
                title=sec["title"],
                level=sec["level"],
                page_number=sec["page"],
                summary=summary,
                content=content_str,
                table_refs=tables,
                footnote_refs=footnotes,
                keywords=keywords
            )
            node_map[node_id] = tree_node

            # Hierarchy stack insertion
            while stack and stack[-1].level >= tree_node.level:
                stack.pop()

            if stack:
                parent = stack[-1]
                tree_node.parent_id = parent.node_id
                parent.children.append(tree_node)
            else:
                root_nodes.append(tree_node)

            stack.append(tree_node)

        doc_title = sections[0]["title"] if sections else filename
        return DocumentTree(
            doc_id=doc_id,
            filename=filename,
            title=doc_title,
            total_pages=max(current_page, 1),
            root_nodes=root_nodes,
            node_map=node_map
        )

    def _generate_extractive_summary(self, title: str, content: str, max_words: int = 40) -> str:
        """Fast rule-based / extractive summarizer without calling expensive external APIs."""
        if not content:
            return f"Section: {title}"
        
        # Take first 2 informative sentences
        sentences = re.split(r"(?<=[.!?])\s+", content)
        clean_sentences = [s.strip() for s in sentences if len(s.strip()) > 15 and not s.startswith("|")]
        if clean_sentences:
            summary = " ".join(clean_sentences[:2])
            words = summary.split()
            if len(words) > max_words:
                summary = " ".join(words[:max_words]) + "..."
            return summary
        return f"{title}: {content[:120].strip()}..."

    def _extract_keywords(self, title: str, content: str) -> List[str]:
        """Extract uppercase identifiers, financial metrics, and domain terms."""
        combined = f"{title} {content}"
        # Match words with capitalized first letters, numbers with units (e.g., $14M, 18%, EBITDA)
        metric_matches = re.findall(r"(\$?\d+(?:\.\d+)?[%MBKmbk]?|[A-Z]{2,10}|[A-Z][a-z]{3,})", combined)
        # Deduplicate while preserving order
        seen = set()
        keywords = []
        stopwords = {"The", "This", "That", "With", "From", "Have", "Were", "Been", "Which", "About", "Their"}
        for k in metric_matches:
            k_clean = k.strip()
            if len(k_clean) > 2 and k_clean not in stopwords and k_clean.lower() not in seen:
                seen.add(k_clean.lower())
                keywords.append(k_clean)
        return keywords[:15]
