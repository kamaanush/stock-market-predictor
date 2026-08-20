#!/bin/bash

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "======================================"
echo " NEXUS AI - AUTOMATED TEST SUITE"
echo "======================================"
echo ""


echo "1/5 BACKEND SYNTAX CHECK"
echo "--------------------------------------"

cd "$ROOT/backend"

python3 -m py_compile app/main.py
python3 -m py_compile app/services/live_market.py
python3 -m py_compile app/services/scanner.py
python3 -m py_compile app/services/scanner_v2.py

echo "✓ Backend syntax passed"
echo ""


echo "2/5 BACKEND PYTEST"
echo "--------------------------------------"

python3 -m pytest -v

echo ""
echo "✓ Backend tests passed"
echo ""


echo "3/5 FRONTEND TYPESCRIPT"
echo "--------------------------------------"

cd "$ROOT/frontend"

npm run typecheck

echo ""
echo "✓ TypeScript passed"
echo ""


echo "4/5 FRONTEND UNIT TESTS"
echo "--------------------------------------"

npm test

echo ""
echo "✓ Frontend tests passed"
echo ""


echo "5/5 PLAYWRIGHT E2E"
echo "--------------------------------------"

npm run test:e2e

echo ""
echo "✓ Browser tests passed"
echo ""


echo "======================================"
echo " ALL NEXUS TESTS PASSED ✓"
echo "======================================"
echo ""
