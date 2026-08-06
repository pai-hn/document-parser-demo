#!/usr/bin/env bash
# Document Parser Demo — frontend + backend 동시 기동
# Usage: ./scripts/dev.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SERVER_DIR="$ROOT_DIR/projects/server"
FRONTEND_DIR="$ROOT_DIR/projects/frontend"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "  종료 중..."
    if [ -n "${BACKEND_PID}" ] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
        kill "${BACKEND_PID}" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID}" ] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        kill "${FRONTEND_PID}" 2>/dev/null || true
    fi
    # uvicorn --reload / vite 자식까지 정리
    local pids
    pids="$(lsof -ti:8080 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        # shellcheck disable=SC2086
        kill $pids 2>/dev/null || true
    fi
    pids="$(lsof -ti:5173 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        # shellcheck disable=SC2086
        kill $pids 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "  종료 완료"
}

trap cleanup EXIT INT TERM

echo ""
echo "  Document Parser Demo 개발 서버"
echo "  ──────────────────────────────────────"
echo ""

if ! command -v uv &>/dev/null; then
    echo "  ! uv가 필요합니다. https://docs.astral.sh/uv/"
    exit 1
fi
if ! command -v bun &>/dev/null; then
    echo "  ! bun이 필요합니다. https://bun.sh/"
    exit 1
fi

if lsof -ti:8080 &>/dev/null; then
    echo "  ! 포트 8080이 이미 사용 중입니다. ./scripts/teardown.sh 후 다시 실행하세요."
    exit 1
fi
if lsof -ti:5173 &>/dev/null; then
    echo "  ! 포트 5173이 이미 사용 중입니다. ./scripts/teardown.sh 후 다시 실행하세요."
    exit 1
fi

if [ ! -f "$SERVER_DIR/.env" ]; then
    if [ -f "$SERVER_DIR/.env.example" ]; then
        cp "$SERVER_DIR/.env.example" "$SERVER_DIR/.env"
        echo "  > .env 생성됨 (.env.example 복사)"
    else
        echo "  ! projects/server/.env 가 없습니다."
        exit 1
    fi
fi

echo "  [1/2] 백엔드 시작  → http://localhost:8080"
(
    cd "$SERVER_DIR"
    # 프로세스 치환으로 로그 prefix — $! 는 uvicorn 쪽 PID 유지
    uv run uvicorn webapp.app:create_app --factory --host 0.0.0.0 --port 8080 --reload \
        > >(sed $'s/^/\033[36m[backend]\033[0m /') \
        2> >(sed $'s/^/\033[36m[backend]\033[0m /' >&2)
) &
BACKEND_PID=$!

echo "  [2/2] 프론트엔드 시작 → http://localhost:5173"
(
    cd "$FRONTEND_DIR"
    bun dev --host \
        > >(sed $'s/^/\033[35m[frontend]\033[0m /') \
        2> >(sed $'s/^/\033[35m[frontend]\033[0m /' >&2)
) &
FRONTEND_PID=$!

echo ""
echo "  ──────────────────────────────────────"
echo "  Ctrl+C 로 둘 다 종료됩니다."
echo "  ──────────────────────────────────────"
echo ""

# macOS 기본 bash(3.2) 호환: 둘 다 종료될 때까지 대기 (Ctrl+C → trap cleanup)
wait
