# My Test Project

Test project for API integration

## 시작하기

```bash
# 원커맨드 세팅
./scripts/setup.sh

# 또는 수동 세팅
cd deploy/docker-compose && docker compose up -d   # 인프라
cd projects/server && uv sync && cp .env.example .env
cd projects/frontend && bun install
```

## 실행

```bash
# 백엔드 (http://localhost:8080)
cd projects/server && uv run uvicorn webapp.app:create_app --factory --host 0.0.0.0 --port 8080 --reload

# 프론트엔드 (http://localhost:5173)
cd projects/frontend && bun dev
```

기본 계정: `master` / `master`

## 문서

- [HELP.md](HELP.md) — 세팅 가이드, 환경 변수, 자주 쓰는 명령어
- [AGENTS.md](AGENTS.md) — 프로젝트 컨벤션, 아키텍처 규칙
- [docs/cookbook/](docs/cookbook/) — **개발자 쿡북** (페이지 추가, 도메인 추가, DataTable 사용법 등)

## 프로젝트 구조

```
my-test-project/
├── projects/
│   ├── server/             # FastAPI 백엔드 (Python 3.13, uv)
│   │   ├── src/            # DDD 도메인 모듈
│   │   ├── webapp/         # FastAPI 앱, 라우터, DTO
│   │   └── tests/
│   └── frontend/           # React 19 (Vite, bun, shadcn/ui)
│       └── src/
│           ├── pages/      # 페이지 컴포넌트
│           ├── components/ # 공용 UI 컴포넌트
│           └── hooks/      # 커스텀 훅
├── deploy/
│   ├── docker-compose/     # 로컬 개발 인프라
│   └── k8s/                # Kubernetes 매니페스트
└── docs/
    └── cookbook/            # 개발자 가이드
```
