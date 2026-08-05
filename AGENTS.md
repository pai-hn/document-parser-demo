# My Test Project

Test project for API integration

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 서버 | Python 3.13, FastAPI, uvicorn, uv |
| 데이터베이스 | PostgreSQL 17, SQLAlchemy async, asyncpg |
| 인증 | PyJWT (HS256), bcrypt |
| DI | dependency-injector (DeclarativeContainer) |
| 프론트엔드 | React 19, Vite, TypeScript strict, Tailwind CSS 4, shadcn/ui |
| 테스트 | pytest-asyncio, testcontainers |
| 린터 | ruff (Python), ESLint + Prettier (TypeScript) |

---

## 설계 원칙

### 도메인 캡슐화

상태 변경은 **도메인 메서드**를 통해서만 수행한다. 서비스에서 필드를 직접 할당하면 안 된다.

```python
# 올바른 방법 — 도메인 메서드 호출
session.start(started_at=now)
session.complete(completed_at=now)

# 잘못된 방법 — 서비스에서 직접 할당
session.status = "running"
```

Entity 계층은 `from_domain()` / `to_domain()` / `update(domain)` 변환만 담당한다.
비즈니스 로직을 Entity나 Repository에 두지 않는다.

### DI 의존성 흐름

```
L0 (인프라)  →  L1 (단일 도메인)  →  L2 (교차 도메인)  →  L3 (오케스트레이터)
  Database        User, Sample         Auth (→User)        GenOrchestrator
  Redis           WizardStep           ScriptGen           SetupOrchestrator
```

하위 계층은 상위 계층을 import하지 않는다. 역방향 의존 금지.

### 얇은 라우터, 풍부한 도메인

라우터(컨트롤러)는 HTTP 파싱·검증·응답 포맷만 처리한다.
비즈니스 판단은 도메인 모델과 서비스에 둔다.

---

## 프로젝트 구조

```
my-test-project/
├── projects/
│   ├── server/             # FastAPI 백엔드
│   │   ├── src/            # 도메인 모듈 (DDD)
│   │   │   └── {domain}/   # domains.py, entities.py, repository.py, service.py, container.py
│   │   ├── webapp/         # FastAPI 앱, 라우터, DTO, DI 컨테이너
│   │   └── tests/          # unit / integration
│   └── frontend/           # React 프론트엔드
│       └── src/
│           ├── pages/      # 페이지 컴포넌트
│           ├── components/ # 공용 UI (DataTable, DatePicker, StatCard ...)
│           ├── hooks/      # 커스텀 훅
│           ├── types/      # 공용 타입
│           └── lib/        # 유틸리티 (format, constants)
├── deploy/
│   ├── docker-compose/     # 로컬 개발 인프라
│   └── k8s/                # Kubernetes (Kustomize)
└── docs/cookbook/           # 개발자 가이드
```

---

## DDD 파일 규칙

새 도메인을 추가할 때 반드시 따라야 하는 구조:

| 파일 | 역할 | 주의사항 |
|------|------|---------|
| `domains.py` | 도메인 모델 (`@dataclass`) | 프레임워크 의존 없음. 상태 전이는 메서드로만 |
| `entities.py` | SQLAlchemy ORM 엔티티 | `from_domain()` / `to_domain()` / `update()` 매핑만 |
| `repository.py` | 데이터 접근 (CRUD) | `BaseRepository` 상속. 커스텀 쿼리만 추가 |
| `service.py` | 비즈니스 로직 | 도메인 메서드 호출 → repo.update() 위임 |
| `container.py` | DI 컨테이너 | `DeclarativeContainer` 상속 |

도메인 모델 상태 전이 예시:

```python
@dataclass
class Sample:
    status: str  # "draft" | "published" | "archived"

    def publish(self, *, updated_at: datetime) -> None:
        if self.status != "draft":
            raise ValueError(f"draft에서만 발행 가능 (현재: {self.status})")
        self.status = "published"
        self.updated_at = updated_at
```

---

## 코딩 컨벤션

### Python

- **ruff**: `line-length = 120`, `select = [E, W, F, I, UP]`
- **패키지 매니저**: `uv`
- **비동기 우선**: I/O 바운드 작업은 `async def`
- **타입 힌트**: 모든 public 함수에 필수
- **Docstring**: Google Style Guide, 한글 작성
- **네이밍**: `snake_case`(함수/변수), `PascalCase`(클래스), `UPPER_SNAKE_CASE`(상수)

### TypeScript

- **ESLint + Prettier**, `strict` 모드
- **Path alias**: `@/` → `src/`
- **네이밍**: `camelCase`(함수/변수), `PascalCase`(컴포넌트/타입)

### DTO

- `CommonModel` 상속, `alias_generator = to_camel`, `populate_by_name = True`
- `from_domain()`: `CommonModel`에서 제공하므로 개별 Response에 중복 정의하지 않음

### Git

- **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- 브랜치: `feat/short-description`, `fix/short-description`
- PR base: `dev` 브랜치

---

## 로컬 개발

```bash
# 인프라
cd deploy/docker-compose && docker compose up -d

# 서버 (http://localhost:8080)
cd projects/server
uv sync && cp .env.example .env
uv run uvicorn webapp.app:create_app --factory --host 0.0.0.0 --port 8080 --reload

# 프론트엔드 (http://localhost:5173)
cd projects/frontend
bun install && bun dev

# 기본 계정: master / master
```

## 테스트 및 린트

```bash
# 서버
cd projects/server
uv run ruff check . && uv run ruff format . && uv run pytest -v

# 프론트엔드
cd projects/frontend
bun lint
```

---

## 권한 체계

| 역할 | 레벨 | 범위 |
|------|------|------|
| `master` | 3 | 시스템 전체 관리, 모든 사용자 CRUD |
| `admin` | 2 | 팀 멤버 관리 |
| `member` | 1 | 일반 기능 사용, 본인 계정 관리 |

권한 검사:
- `get_current_user` — 로그인 필수
- `require_min_role("admin")` — 최소 역할 레벨
- `require_role("master")` — 정확한 역할 일치

---

## 참고 문서

- [docs/cookbook/](docs/cookbook/) — 개발자 쿡북 (페이지 추가, 도메인 추가, 배포 등)
- [HELP.md](HELP.md) — 환경 설정, 자주 쓰는 명령어
