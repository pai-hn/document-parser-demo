# Kubernetes에 배포하기

개발/운영 환경의 Kubernetes 클러스터에 배포하는 방법입니다.
Kustomize overlay로 환경별 설정을 관리합니다.

> 로컬에서 kind로 테스트하려면 [로컬에서 Kind로 배포하기](kind-deploy.md)를 참고하세요.

---

## 디렉토리 구조

```
deploy/k8s/
├── base/                           # 공통 매니페스트
│   ├── kustomization.yaml          # 리소스 목록 + init.sql ConfigMap
│   ├── namespace.yaml
│   ├── postgres/
│   │   ├── statefulset.yaml        # PVC + init.sql 마운트
│   │   └── service.yaml
│   ├── server/
│   │   ├── deployment.yaml         # FastAPI 서버
│   │   └── service.yaml
│   └── frontend/
│       ├── deployment.yaml         # nginx 프론트엔드
│       └── service.yaml
└── overlays/
    ├── local/                      # kind 로컬 테스트용
    └── dev/                        # 개발 서버용
        ├── kustomization.yaml
        └── ingressroute.yaml       # Traefik IngressRoute
```

---

## 1단계: Docker 이미지 빌드 및 푸시

```bash
# 이미지 빌드
docker build -t registry.example.com/my-test-project-api:v1.0.0 projects/server/
docker build -t registry.example.com/my-test-project-frontend:v1.0.0 projects/frontend/

# 레지스트리에 푸시
docker push registry.example.com/my-test-project-api:v1.0.0
docker push registry.example.com/my-test-project-frontend:v1.0.0
```

---

## 2단계: 환경별 overlay 설정

`deploy/k8s/overlays/dev/kustomization.yaml`에서 이미지와 환경을 오버라이드합니다.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
  - ingressroute.yaml

images:
  - name: my-test-project-api
    newName: registry.example.com/my-test-project-api
    newTag: v1.0.0
  - name: my-test-project-frontend
    newName: registry.example.com/my-test-project-frontend
    newTag: v1.0.0

patches:
  # DB 비밀번호를 Secret 참조로 교체
  - target:
      kind: Deployment
      name: server
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/env/2
        value:
          name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
      - op: replace
        path: /spec/template/spec/containers/0/env/5
        value:
          name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: secret-key
```

---

## 3단계: Secret 생성

민감한 값은 Secret으로 관리합니다.

```bash
# DB 비밀번호
kubectl -n my-test-project-devcreate secret generic db-credentials \
  --from-literal=password=your-secure-password

# JWT 시크릿 키
kubectl -n my-test-project-devcreate secret generic jwt-secret \
  --from-literal=secret-key=your-jwt-secret-key
```

---

## 4단계: 배포

```bash
# 매니페스트 미리보기
kubectl kustomize deploy/k8s/overlays/dev

# 배포
kubectl apply -k deploy/k8s/overlays/dev

# 상태 확인
kubectl -n my-test-project-devget pods
kubectl -n my-test-project-devrollout status deployment/my-test-project-api
```

---

## 업데이트 배포

```bash
# 새 이미지 빌드 및 푸시
docker build -t registry.example.com/my-test-project-api:v1.1.0 projects/server/
docker push registry.example.com/my-test-project-api:v1.1.0

# kustomization.yaml의 newTag를 v1.1.0으로 변경 후
kubectl apply -k deploy/k8s/overlays/dev

# 또는 이미지만 직접 교체
kubectl -n my-test-project-devset image deployment/my-test-project-api \
  server=registry.example.com/my-test-project-api:v1.1.0
```

---

## 새 환경 추가하기 (staging, production)

```bash
mkdir -p deploy/k8s/overlays/staging
```

`deploy/k8s/overlays/staging/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base

namespace: my-test-project-stg

images:
  - name: my-test-project-api
    newName: registry.example.com/my-test-project-api
    newTag: v1.0.0-rc1

patches:
  # replica 수 조정
  - target:
      kind: Deployment
      name: server
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 2
  # PostgreSQL 스토리지 증가
  - target:
      kind: StatefulSet
      name: postgres
    patch: |-
      - op: replace
        path: /spec/volumeClaimTemplates/0/spec/resources/requests/storage
        value: 10Gi
```

```bash
kubectl apply -k deploy/k8s/overlays/staging
```

---

## 운영 체크리스트

- [ ] Secret으로 민감한 값 관리 (DB_PASSWORD, JWT_SECRET_KEY)
- [ ] 이미지 태그에 `latest` 대신 버전 사용 (v1.0.0)
- [ ] PostgreSQL PVC 크기 적절히 설정
- [ ] Ingress/IngressRoute 설정 (도메인, TLS)
- [ ] 리소스 제한 설정 (resources.limits/requests)
- [ ] replicas 조정 (운영은 최소 2개)
