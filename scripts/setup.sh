#!/usr/bin/env bash
# My Test Project — 개발환경 원커맨드 세팅
# Usage: ./scripts/setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "  My Test Project 개발환경 세팅"
echo "  ──────────────────────────────────────"
echo ""

# ── 1. 인프라 (Docker Compose) ─────────────────────────────────────────
echo "  [1/4] 인프라 서비스 시작"
if command -v docker &>/dev/null; then
    COMPOSE_FILE="$ROOT_DIR/deploy/docker-compose/docker-compose.yml"
    docker compose -f "$COMPOSE_FILE" up -d
    echo "        > Docker Compose 서비스 시작됨"
    echo "        > healthcheck 대기 중..."
    sleep 5

    # DB 존재 여부 확인
    DB_NAME="my_test_project"
    if docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -lqt 2>/dev/null | grep -qw "$DB_NAME"; then
        echo "        > 데이터베이스 '$DB_NAME' 확인됨"
    else
        echo "        ! 데이터베이스 '$DB_NAME'가 존재하지 않습니다."
        echo "        ! 기존 볼륨이 다른 프로젝트의 DB를 포함하고 있을 수 있습니다."
        echo ""
        echo "        해결 방법:"
        echo "          docker compose -f deploy/docker-compose/docker-compose.yml down -v"
        echo "          docker compose -f deploy/docker-compose/docker-compose.yml up -d"
        echo ""
        echo "        주의: -v 옵션은 기존 데이터를 삭제합니다."
    fi
else
    echo "        ! Docker가 설치되어 있지 않습니다. 수동으로 인프라를 세팅하세요."
fi

# ── 2. 백엔드 의존성 ───────────────────────────────────────────────────
echo ""
echo "  [2/4] 백엔드 의존성 설치"
cd "$ROOT_DIR/projects/server"

if command -v uv &>/dev/null; then
    uv sync
    echo "        > Python 의존성 설치 완료"
else
    echo "        ! uv가 설치되어 있지 않습니다. https://docs.astral.sh/uv/"
    exit 1
fi

# .env 파일 생성 (없을 때만)
if [ ! -f .env ]; then
    cp .env.example .env
    echo "        > .env 파일 생성됨 (.env.example 복사)"
else
    echo "        > .env 파일 이미 존재"
fi

# ── 3. 프론트엔드 의존성 ──────────────────────────────────────────────
echo ""
echo "  [3/4] 프론트엔드 의존성 설치"
cd "$ROOT_DIR/projects/frontend"

if command -v bun &>/dev/null; then
    bun install
    echo "        > 프론트엔드 의존성 설치 완료"
else
    echo "        ! bun가 설치되어 있지 않습니다."
fi

# ── 4. 검증 ───────────────────────────────────────────────────────────
echo ""
echo "  [4/4] 환경 검증"
cd "$ROOT_DIR/projects/server"

uv run python -c "from webapp.app import create_app; print('        > FastAPI 앱 import 성공')" 2>/dev/null \
    || echo "        ! FastAPI 앱 import 실패 — .env 설정을 확인하세요"

uv run ruff check . --quiet && echo "        > ruff 린트 통과" \
    || echo "        ! ruff 린트 에러 — 'uv run ruff check .' 로 확인하세요"

echo ""
echo "  ──────────────────────────────────────"
echo "  세팅 완료"
echo ""
echo "  서버:   cd projects/server && uv run uvicorn webapp.app:create_app --factory --host 0.0.0.0 --port 8080 --reload"
echo "  프론트: cd projects/frontend && bun dev"
echo "  테스트: cd projects/server && uv run pytest tests/ -v"
echo "  ──────────────────────────────────────"
echo ""
