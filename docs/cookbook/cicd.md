# CI/CD 파이프라인

GitHub Actions 워크플로우 구성과 커스터마이징 방법입니다.

---

## 기본 제공 워크플로우

`.github/workflows/` 디렉토리에 3개의 워크플로우가 있습니다.

### 서버 검증 (`validate_projects.yml`)

PR이 올라오면 자동으로 실행됩니다.

```yaml
# 실행 조건: main/dev 브랜치로의 PR
on:
  pull_request:
    branches: [main, dev]
    paths: ["projects/server/**"]

# 수행 작업:
# 1. Python 3.13 + uv 설치
# 2. uv sync (의존성 설치)
# 3. ruff check (린트)
# 4. ruff format --check (포맷 검사)
# 5. pytest (테스트)
```

### 프론트엔드 검증 (`validate_frontend.yml`)

```yaml
on:
  pull_request:
    branches: [main, dev]
    paths: ["projects/frontend/**"]

# 수행 작업:
# 1. Node 22 + pnpm 설치
# 2. pnpm install
# 3. pnpm lint (ESLint)
# 4. pnpm build (타입 체크 + 빌드)
```

### 개발 빌드 및 배포 (`dev_build_projects.yml`)

dev 브랜치에 머지되면 Harbor에 이미지를 빌드·푸시하고 K8s rollout restart를 수행합니다.

이미지 태그: `harbor.pai-world.com/<project>/<project>-api:<commit-sha>`

---

## 로컬에서 CI 검증하기

PR을 올리기 전에 로컬에서 같은 검사를 실행할 수 있습니다.

```bash
# 서버
cd projects/server
uv run ruff check .
uv run ruff format . --check
uv run pytest -v

# 프론트엔드
cd projects/frontend
pnpm lint
pnpm build
```
