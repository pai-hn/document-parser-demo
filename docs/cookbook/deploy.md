# 로컬 개발 및 테스트

프로젝트를 로컬에서 실행하고, 테스트하고, 빌드하는 방법입니다.

---

## 인프라 기동

```bash
cd deploy/docker-compose
docker compose up -d
```

PostgreSQL이 실행됩니다. `init.sql`의 스키마가 자동으로 적용됩니다.

```bash
# 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f postgres

# 인프라 중지 (데이터 유지)
docker compose down

# 인프라 중지 + 데이터 삭제 (DB 초기화)
docker compose down -v
```

> DB 스키마를 변경했다면 `docker compose down -v && docker compose up -d`로 재생성합니다.

---

## 백엔드 서버 실행

```bash
cd projects/server

# 의존성 설치
uv sync

# 환경변수 설정 (최초 1회)
cp .env.example .env

# 서버 시작 (자동 리로드)
uv run uvicorn webapp.app:create_app --factory --reload --host 0.0.0.0 --port 8080
```

- API: http://localhost:8080
- Swagger 문서: http://localhost:8080/docs
- 기본 계정: `master` / `master` (첫 실행 시 자동 생성)

---

## 프론트엔드 실행

```bash
cd projects/frontend

# 의존성 설치
bun install

# 개발 서버 시작
bun dev
```

- 프론트엔드: http://localhost:5173
- 백엔드가 실행 중이어야 로그인이 가능합니다.

---

## 테스트

### 백엔드 테스트

```bash
cd projects/server

# 전체 테스트 실행
uv run pytest

# 상세 출력
uv run pytest -v

# 특정 파일만
uv run pytest tests/test_sample.py -v

# 특정 테스트만
uv run pytest tests/test_sample.py::test_create_sample -v
```

### 프론트엔드 린트

```bash
cd projects/frontend
bun lint
```

---

## 린트 & 포맷

### Python (ruff)

```bash
cd projects/server

# 린트 검사
uv run ruff check .

# 린트 자동 수정
uv run ruff check . --fix

# 코드 포맷
uv run ruff format .
```

### TypeScript (ESLint)

```bash
cd projects/frontend

# 린트 검사
bun lint
```

---

## API 테스트 (curl)

서버가 실행 중일 때 터미널에서 직접 API를 호출할 수 있습니다.

```bash
# 1) 로그인 → 토큰 받기
TOKEN=$(curl -s -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"master","password":"master"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

echo $TOKEN

# 2) 샘플 생성
curl -X POST http://localhost:8080/samples \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"테스트","content":"내용"}'

# 3) 샘플 목록 조회
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/samples

# 4) 헬스체크
curl http://localhost:8080/health
```

---

## 프로덕션 빌드

### 프론트엔드

```bash
cd projects/frontend
bun build
# → dist/ 폴더에 정적 파일 생성
```

### Docker 이미지 (참고)

```bash
# 서버
docker build -t my-test-project-server -f projects/server/Dockerfile projects/server

# 프론트엔드
docker build -t my-test-project-frontend -f projects/frontend/Dockerfile projects/frontend
```

---

## 자주 겪는 문제

### "column ... does not exist" 에러

DB 스키마와 코드가 맞지 않을 때 발생합니다.

```bash
# DB를 삭제하고 다시 생성
cd deploy/docker-compose
docker compose down -v && docker compose up -d
```

### 서버가 시작되지 않음

```bash
# 환경변수 확인
cat projects/server/.env

# DB 연결 확인
docker compose -f deploy/docker-compose/docker-compose.yml ps
```

### 프론트엔드 로그인 실패

- 백엔드가 실행 중인지 확인 (`http://localhost:8080/health`)
- 기본 계정: `master` / `master`
- 네트워크 에러가 아닌 401이면 비밀번호를 확인하세요.
