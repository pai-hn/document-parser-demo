# 로컬에서 Kind로 배포하기

Docker Compose 대신 Kubernetes 환경에서 테스트하고 싶을 때,
kind(Kubernetes IN Docker)로 로컬에 클러스터를 만들어 배포하는 방법입니다.

---

## 사전 요구사항

```bash
brew install kind kubectl
```

---

## 1단계: kind 클러스터 생성

```bash
kind create cluster --name my-test-project --config deploy/k8s/overlays/local/kind-cluster.yaml
```

`kind-cluster.yaml`이 NodePort를 호스트에 매핑해서, 배포 후 다음 주소로 접근할 수 있습니다.

| 서비스 | 주소 |
|--------|------|
| 서버 API | http://localhost:8080 |
| 프론트엔드 | http://localhost:3000 |

---

## 2단계: Docker 이미지 빌드 + kind에 로드

kind는 로컬 Docker 이미지를 자동으로 사용하지 않습니다. 빌드 후 명시적으로 로드해야 합니다.

```bash
# 이미지 빌드
docker build -t my-test-project-api:latest projects/server/
docker build -t my-test-project-frontend:latest projects/frontend/

# kind에 로드
kind load docker-image my-test-project-api:latest --name my-test-project
kind load docker-image my-test-project-frontend:latest --name my-test-project
```

> 이미지 태그가 `deploy/k8s/base/server/deployment.yaml`의 `image:` 값과 일치해야 합니다.

---

## 3단계: 배포

```bash
kubectl apply -k deploy/k8s/overlays/local
```

배포되는 리소스:
- **PostgreSQL StatefulSet** — 1Gi PVC, init.sql 자동 실행
- **Server Deployment** — FastAPI (NodePort 30080 → localhost:8080)
- **Frontend Deployment** — nginx (NodePort 30000 → localhost:3000)

---

## 4단계: 상태 확인

```bash
# Pod 상태 확인 (네임스페이스는 프로젝트 slug)
kubectl -n my-test-project-devget pods

# 전부 Running/Ready가 될 때까지 기다리기
kubectl -n my-test-project-devwait --for=condition=ready pod --all --timeout=120s

# 접속 확인
curl http://localhost:8080/health
open http://localhost:3000
# 로그인: master / master
```

문제가 있으면:

```bash
# Pod 로그
kubectl -n my-test-project-devlogs deployment/my-test-project-api

# postgres 로그
kubectl -n my-test-project-devlogs my-test-project-database-0

# 이벤트 (이미지 풀 실패 등)
kubectl -n my-test-project-devget events --sort-by='.lastTimestamp'
```

---

## 코드 수정 후 재배포

```bash
docker build -t my-test-project-api:latest projects/server/
kind load docker-image my-test-project-api:latest --name my-test-project
kubectl -n my-test-project-devrollout restart deployment/my-test-project-api
```

프론트엔드도 동일한 방식입니다.

---

## DB 초기화 (테이블 재생성)

init.sql을 수정했다면 PostgreSQL PVC를 삭제하고 Pod를 재생성합니다.

```bash
kubectl -n my-test-project-devdelete pvc pgdata-my-test-project-database-0
kubectl -n my-test-project-devdelete pod my-test-project-database-0
# StatefulSet이 새 Pod를 자동 생성하고 init.sql을 다시 실행합니다
```

---

## 정리

```bash
# 리소스만 삭제
kubectl delete -k deploy/k8s/overlays/local

# kind 클러스터 전체 삭제
kind delete cluster --name my-test-project
```

---

## 자주 겪는 문제

### ImagePullBackOff

이미지가 kind에 로드되지 않았습니다.

```bash
# kind 안에 이미지가 있는지 확인
docker exec my-test-project-control-plane crictl images | grep my-test-project

# 없으면 다시 로드
kind load docker-image my-test-project-api:latest --name my-test-project
```

### CrashLoopBackOff

```bash
kubectl -n my-test-project-devlogs deployment/my-test-project-api --previous
# DB 연결 실패라면 postgres Pod가 Ready인지 확인
```

### column does not exist

init.sql이 실행되지 않았습니다.

```bash
# ConfigMap 확인
kubectl -n my-test-project-devget configmap postgres-init -o yaml

# init.sql 마운트 확인
kubectl -n my-test-project-devexec my-test-project-database-0 -- ls /docker-entrypoint-initdb.d/
```
