# 시작 가이드 — My Test Project

Test project for API integration

## 사전 요구사항

| 도구 | 버전 | 용도 |
|------|------|------|
| Python | 3.13+ | 서버 런타임 |
| [uv](https://docs.astral.sh/uv/) | latest | Python 패키지 매니저 |
| Node.js | 22+ | 프론트엔드 런타임 |
| bun | latest | 프론트엔드 패키지 매니저 |
| Docker Desktop | latest | 로컬 인프라 |

## 빠른 시작

### 1. 인프라 기동

```bash
docker compose -f deploy/docker-compose/docker-compose.yml up -d
```

기동되는 서비스:
- **PostgreSQL 17** — 포트 `5432`

### 2. 백엔드 서버 시작

```bash
cd projects/server
uv sync
uv run uvicorn webapp.app:create_app --factory --reload --host 0.0.0.0 --port 8080
```

API: [http://localhost:8080](http://localhost:8080) | API 문서: [http://localhost:8080/docs](http://localhost:8080/docs)

### 3. 프론트엔드 시작

```bash
cd projects/frontend
bun install
bun dev
```

프론트엔드: [http://localhost:5173](http://localhost:5173)

## 프로젝트 구조

```
my-test-project/
├── projects/
│   ├── server/          # FastAPI 백엔드
│   └── frontend/        # React 프론트엔드
├── deploy/
│   ├── docker-compose/  # 로컬 개발 인프라
│   └── k8s/             # Kubernetes 매니페스트
├── AGENTS.md            # 프로젝트 컨벤션, 아키텍처 규칙
└── HELP.md              # 이 파일
```

## 자주 사용하는 명령어

### 서버 테스트

```bash
cd projects/server
uv run pytest
```

### 린트 & 포맷

```bash
cd projects/server
uv run ruff check .
uv run ruff format .
```

### 프론트엔드 린트

```bash
cd projects/frontend
bun lint
```

## 개발자 쿡북

`docs/cookbook/` 디렉토리에 실전 개발 가이드가 있습니다.

| 가이드 | 설명 |
|--------|------|
| [새 페이지 추가](docs/cookbook/add-page.md) | 프론트엔드 페이지 + 사이드바 연결 |
| [새 도메인 추가](docs/cookbook/add-domain.md) | 백엔드 DDD 도메인 전체 과정 |
| [DataTable 사용](docs/cookbook/data-table.md) | 정렬·검색·날짜필터 테이블 |
| [배포 및 테스트](docs/cookbook/deploy.md) | 인프라, 서버, 프론트, 테스트, 빌드 |

## 환경 변수

`.env.example`을 복사하여 값을 설정하세요:

```bash
cp projects/server/.env.example projects/server/.env
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DB_HOST` | `localhost` | PostgreSQL 호스트 |
| `DB_PORT` | `5432` | PostgreSQL 포트 |
| `DB_NAME` | `my_test_project` | 데이터베이스명 |
| `DB_USER` | `postgres` | 데이터베이스 사용자 |
| `DB_PASSWORD` | `postgres` | 데이터베이스 비밀번호 |
