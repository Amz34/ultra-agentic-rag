#!/usr/bin/env bash
# ==============================================================================
# Enterprise Verification Suite - Frictionless Offline / Mock Verification
# Usage: ./scripts/verify_enterprise.sh [--mock]
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MOCK_FLAG="${1:-}"

export MOCK_MODE=1
export PYTHONUNBUFFERED=1
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

echo "======================================================================"
echo "⚡ RUNNING ENTERPRISE VERIFICATION SUITE: ultra-agentic-rag"
echo "   Mode: MOCK_MODE=${MOCK_MODE} (Zero Credentials / Offline Verification)"
echo "   Root: ${REPO_ROOT}"
echo "======================================================================"

cd "${REPO_ROOT}"

echo ""
echo "[Step 1/3] Running Unit & Integration Test Suite..."
python3 -m unittest tests/test_ultra_hybrid_rag.py -v

echo ""
echo "[Step 2/3] Executing Offline SEC 10-K RAG Benchmark..."
python3 -m ultra_hybrid_rag.cli benchmark

echo ""
echo "[Step 3/3] Validating Document Tree & Multi-Hop Query Synthesis..."
python3 -c "
import json
from ultra_hybrid_rag.engine import UltraHybridRAG

engine = UltraHybridRAG()
doc = '''# ACME Financial Summary
[Page 1]
Executive Summary: Fiscal 2026 was resilient.
## Operating Income
[Page 2]
Operating income was \$450M. See Note 3 for restructuring costs.
## Note 3: Restructuring
[Page 8]
Restructuring charges were \$12M under IFRS standard.
'''
tree = engine.index_document(doc, filename='quick_verify.md')
assert len(tree.node_map) == 3, f'Expected 3 nodes, got {len(tree.node_map)}'
res = engine.query('Summarize operating income and restructuring charges', doc_id=tree.doc_id)
assert res.confidence >= 0.70, f'Expected confidence >= 0.70, got {res.confidence}'
print(f'✓ Verified End-to-End: query strategy={res.strategy}, confidence={res.confidence*100:.1f}%, citations={len(res.citations)}')
"

echo ""
echo "======================================================================"
echo "✅ ENTERPRISE VERIFICATION SUITE PASSED (ultra-agentic-rag)"
echo "======================================================================"
