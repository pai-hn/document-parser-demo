# 개발자 쿡북

이 프로젝트를 개발하면서 자주 하게 되는 작업을 단계별로 안내합니다.

---

## 처음이라면 이 순서대로 읽으세요

| 순서 | 가이드 | 배우는 것 |
|:----:|--------|----------|
| 1 | [로컬 개발 및 테스트](deploy.md) | 인프라 기동, 서버·프론트 실행, 로그인 확인 |
| 2 | [프로젝트 구조와 환경 변수](env-config.md) | 설정 파일 위치, .env 관리, 새 설정 추가 |
| 3 | [UI 컴포넌트 카탈로그](ui-components.md) | Button, Input, Card, Badge 등 사용법 |
| 4 | [DataTable 사용하기](data-table.md) | 정렬·검색·날짜필터 테이블 만들기 |
| 5 | [폼 입력과 검증](forms.md) | 폼 상태 관리, 클라이언트·서버 검증 |
| 6 | [새 페이지 추가하기](add-page.md) | DB → 백엔드 → 프론트 → 사이드바 (풀스택) |
| 7 | [새 도메인 추가하기](add-domain.md) | 백엔드 DDD 구조 상세 (도메인·엔티티·레포·서비스) |
| 8 | [인증과 권한 관리](auth-and-roles.md) | JWT 인증, 역할별 접근 제어, 라우트 보호 |
| 9 | [테스트 작성하기](testing.md) | 도메인 단위 테스트, DB 통합 테스트, API 테스트 |

---

## 주제별 가이드

### 프론트엔드 패턴

| 가이드 | 설명 |
|--------|------|
| [UI 컴포넌트 카탈로그](ui-components.md) | 모든 공용 컴포넌트와 사용 예시 |
| [DataTable 사용하기](data-table.md) | 정렬, 텍스트 검색, 날짜 범위 필터 |
| [다이얼로그 패턴](dialogs.md) | 확인 모달, 입력 폼 모달, 삭제 확인 |
| [폼 입력과 검증](forms.md) | 기본 폼, 접이식 폼, 비밀번호 폼 |
| [API 클라이언트 구조](api-client.md) | 토큰 자동 갱신, 에러 추출, 파일 업로드 |

### 백엔드 패턴

| 가이드 | 설명 |
|--------|------|
| [새 도메인 추가하기](add-domain.md) | DDD 전체 과정 (domains → entities → repo → service → router) |
| [상태 머신 패턴](state-machine.md) | 도메인 모델의 상태 전이 설계와 구현 |
| [관계가 있는 엔티티](entity-relations.md) | FK, JOIN, 프론트에서 관계 데이터 표시 |
| [인증과 권한 관리](auth-and-roles.md) | JWT, 역할 검사, 본인 리소스 보호 |
| [에러 처리](error-handling.md) | 예외 계층, 전역 핸들러, 프론트 에러 핸들링 |
| [환경 변수 관리](env-config.md) | pydantic-settings, .env, 새 설정 추가 |

### 인프라 연동

| 가이드 | 설명 |
|--------|------|
| [파일 업로드 (MinIO)](file-upload.md) | S3 호환 스토리지로 파일 업로드 |
| [캐싱 (Redis)](caching.md) | 자주 조회하는 데이터를 Redis로 캐싱 |
| [전문 검색 (Elasticsearch)](search.md) | Elasticsearch로 텍스트 검색 |

### 배포와 운영

| 가이드 | 설명 |
|--------|------|
| [로컬 개발 및 테스트](deploy.md) | Docker Compose, 서버·프론트 실행, curl 테스트 |
| [테스트 작성하기](testing.md) | pytest, testcontainers, API 테스트 |
| [CI/CD 파이프라인](cicd.md) | GitHub Actions 워크플로우, 로컬 검증 |
| [로컬에서 Kind로 배포하기](kind-deploy.md) | kind 클러스터 생성, 이미지 로드, NodePort 접근 |
| [Kubernetes에 배포하기](k8s-deploy.md) | 레지스트리 푸시, overlay 설정, Secret 관리, 환경 추가 |
