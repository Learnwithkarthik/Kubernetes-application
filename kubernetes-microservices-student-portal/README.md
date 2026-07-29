# Kubernetes Microservices Student Portal

Teaching-friendly real-time application for Kubernetes hands-on demos.

## Architecture

- Frontend: NGINX + HTML/CSS/JavaScript
- User Service: FastAPI
- Course Service: FastAPI
- Enrollment Service: FastAPI
- Database: PostgreSQL

```text
Browser -> Frontend -> User Service
                   -> Course Service
                   -> Enrollment Service -> User/Course Services
All backend services -> PostgreSQL
```

## Build images

```bash
docker build -t YOUR_DOCKERHUB_USERNAME/student-frontend:v1 ./frontend
docker build -t YOUR_DOCKERHUB_USERNAME/user-service:v1 ./services/user-service
docker build -t YOUR_DOCKERHUB_USERNAME/course-service:v1 ./services/course-service
docker build -t YOUR_DOCKERHUB_USERNAME/enrollment-service:v1 ./services/enrollment-service
```

Push the images and replace `YOUR_DOCKERHUB_USERNAME` in the Kubernetes YAML files.

## Deploy

```bash
kubectl apply -f kubernetes/00-namespace.yaml
kubectl apply -f kubernetes/01-configmap.yaml
kubectl apply -f kubernetes/02-secret.yaml
kubectl apply -f kubernetes/03-postgres.yaml
kubectl apply -f kubernetes/10-user-service.yaml
kubectl apply -f kubernetes/11-course-service.yaml
kubectl apply -f kubernetes/12-enrollment-service.yaml
kubectl apply -f kubernetes/13-frontend.yaml
kubectl get all -n student-portal
kubectl port-forward -n student-portal service/frontend 8080:80
```

Open `http://localhost:8080`.

Advanced manifests include Ingress, HPA, NetworkPolicy, RBAC, Job and CronJob.
