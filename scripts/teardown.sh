#!/usr/bin/env bash
# My Test Project — 서비스 전체 종료
# Usage: ./scripts/teardown.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo "  My Test Project 서비스 종료"
echo "  ──────────────────────────────────────"
echo ""

# ── 1. 백엔드 서버 종료 ───────────────────────────────────────────────
echo "  [1/3] 백엔드 서버 종료"
PID=$(lsof -ti:8080 2>/dev/null || true)
if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null && echo "        > PID $PID 종료됨" || echo "        > 종료 실패 (권한 확인)"
else
    echo "        > 8080 포트에 실행 중인 프로세스 없음"
fi

# ── 2. 프론트엔드 서버 종료 ───────────────────────────────────────────
echo ""
echo "  [2/3] 프론트엔드 서버 종료"
PID=$(lsof -ti:5173 2>/dev/null || true)
if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null && echo "        > PID $PID 종료됨" || echo "        > 종료 실패 (권한 확인)"
else
    echo "        > 5173 포트에 실행 중인 프로세스 없음"
fi

# ── 3. Docker Compose 종료 ────────────────────────────────────────────
echo ""
echo "  [3/3] 인프라 서비스 종료"
if command -v docker &>/dev/null; then
    docker compose -f "$ROOT_DIR/deploy/docker-compose/docker-compose.yml" down
    echo "        > Docker Compose 서비스 종료됨"
else
    echo "        > Docker 없음 (스킵)"
fi

echo ""
echo "  ──────────────────────────────────────"
echo "  종료 완료"
echo ""
echo "  데이터 볼륨은 유지됩니다."
echo "  볼륨까지 삭제하려면: docker compose -f deploy/docker-compose/docker-compose.yml down -v"
echo "  ──────────────────────────────────────"
echo ""
