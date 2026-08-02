import os
import socket
import time
from contextlib import contextmanager

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(
    title="Enrollment Service",
    version="2.0.0"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://portaluser:portalpass@postgres:5432/studentportal"
)

USER_SERVICE_URL = os.getenv(
    "USER_SERVICE_URL",
    "http://user-service:8000"
)

COURSE_SERVICE_URL = os.getenv(
    "COURSE_SERVICE_URL",
    "http://course-service:8000"
)

APP_VERSION = os.getenv("APP_VERSION", "v1")
POD_NAME = os.getenv("POD_NAME", socket.gethostname())
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "unknown")
NODE_NAME = os.getenv("NODE_NAME", "unknown")


class EnrollmentCreate(BaseModel):
    user_id: int
    course_id: int


@contextmanager
def db():
    with psycopg.connect(DATABASE_URL) as connection:
        yield connection


def initialize_database():
    last_error = None

    for attempt in range(1, 31):
        try:
            with db() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS enrollments (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        enrolled_at TIMESTAMP
                            DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, course_id)
                    )
                    """
                )
                connection.commit()

            print(
                f"Database initialized successfully. "
                f"service=enrollment-service "
                f"pod={POD_NAME} "
                f"version={APP_VERSION}"
            )
            return

        except Exception as error:
            last_error = error

            print(
                f"Database connection attempt "
                f"{attempt}/30 failed: {error}"
            )

            time.sleep(2)

    raise RuntimeError(
        f"Database unavailable after 30 attempts: {last_error}"
    )


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def root():
    return {
        "message": "Enrollment Service is running",
        "service": "enrollment-service",
        "version": APP_VERSION,
        "pod": POD_NAME
    }


@app.get("/live")
def liveness():
    return {
        "service": "enrollment-service",
        "status": "alive",
        "pod": POD_NAME
    }


@app.get("/ready")
def readiness():
    try:
        with db() as connection:
            connection.execute("SELECT 1").fetchone()

        return {
            "service": "enrollment-service",
            "status": "ready",
            "pod": POD_NAME
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {error}"
        )


@app.get("/health")
def health():
    return {
        "service": "enrollment-service",
        "status": "healthy",
        "pod": POD_NAME
    }


@app.get("/instance")
def instance():
    return {
        "service": "enrollment-service",
        "version": APP_VERSION,
        "pod": POD_NAME,
        "namespace": POD_NAMESPACE,
        "node": NODE_NAME
    }


@app.get("/version")
def version():
    return {
        "service": "enrollment-service",
        "version": APP_VERSION,
        "pod": POD_NAME
    }


def get_service_data(url: str, resource_name: str):
    try:
        response = httpx.get(
            url,
            timeout=5
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail=f"{resource_name} service unavailable"
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=400,
            detail=f"{resource_name} does not exist"
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=503,
            detail=f"{resource_name} service error"
        )

    return response.json()


@app.post("/enrollments", status_code=201)
def create_enrollment(enrollment: EnrollmentCreate):
    student = get_service_data(
        f"{USER_SERVICE_URL}/users/{enrollment.user_id}",
        "Student"
    )

    course = get_service_data(
        f"{COURSE_SERVICE_URL}/courses/{enrollment.course_id}",
        "Course"
    )

    try:
        with db() as connection:
            row = connection.execute(
                """
                INSERT INTO enrollments (
                    user_id,
                    course_id
                )
                VALUES (%s, %s)
                RETURNING
                    id,
                    user_id,
                    course_id,
                    enrolled_at
                """,
                (
                    enrollment.user_id,
                    enrollment.course_id
                )
            ).fetchone()

            connection.commit()

    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Student already enrolled"
        )

    return {
        "id": row[0],
        "user_id": row[1],
        "student_name": student["name"],
        "course_id": row[2],
        "course_title": course["title"],
        "enrolled_at": row[3]
    }


@app.get("/enrollments")
def list_enrollments():
    with db() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, course_id, enrolled_at
            FROM enrollments
            ORDER BY id
            """
        ).fetchall()

    enrollments = []

    for row in rows:
        student = get_service_data(
            f"{USER_SERVICE_URL}/users/{row[1]}",
            "Student"
        )

        course = get_service_data(
            f"{COURSE_SERVICE_URL}/courses/{row[2]}",
            "Course"
        )

        enrollments.append(
            {
                "id": row[0],
                "user_id": row[1],
                "student_name": student["name"],
                "course_id": row[2],
                "course_title": course["title"],
                "enrolled_at": row[3]
            }
        )

    return enrollments
