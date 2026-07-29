# Kubernetes-application

docker run -d \
  --name postgres \
  --network student-portal-network \
  -e POSTGRES_DB=studentportal \
  -e POSTGRES_USER=portaluser \
  -e POSTGRES_PASSWORD=portalpass \
  -v student-portal-db:/var/lib/postgresql/data \
  postgres:16-alpine


docker build -t user-service:v1 ./services/user-service
docker build -t course-service:v1 ./services/course-service
docker build -t enrollment-service:v1 ./services/enrollment-service
docker build -t student-frontend:v1 ./frontend

docker run -d \
  --name user-service \
  --network student-portal-network \
  -e DATABASE_URL=postgresql://portaluser:portalpass@postgres:5432/studentportal \
  user-service:v1


docker run -d \
  --name course-service \
  --network student-portal-network \
  -e DATABASE_URL=postgresql://portaluser:portalpass@postgres:5432/studentportal \
  course-service:v1

docker run -d \
  --name enrollment-service \
  --network student-portal-network \
  -e DATABASE_URL=postgresql://portaluser:portalpass@postgres:5432/studentportal \
  -e USER_SERVICE_URL=http://user-service:8000 \
  -e COURSE_SERVICE_URL=http://course-service:8000 \
  enrollment-service:v1

docker run -d \
  --name student-frontend \
  --network student-portal-network \
  -p 8080:80 \
  student-frontend:v1


  


  
