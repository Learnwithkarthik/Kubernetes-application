import os
import socket
import time
from contextlib import contextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(
    title="Course Service",
    version="2.0.0"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://portaluser:portalpass@postgres:5432/studentportal"
)

APP_VERSION = os.getenv("APP_VERSION", "v1")
POD_NAME = os.getenv("POD_NAME", socket.gethostname())
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "unknown")
NODE_NAME = os.getenv("NODE_NAME", "unknown")


class CourseCreate(BaseModel):
    title: str
    description: str


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
                    CREATE TABLE IF NOT EXISTS courses (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(160) NOT NULL,
                        description TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                connection.commit()

            print(
                f"Database initialized successfully. "
                f"service=course-service "
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
        "message": "Course Service is running",
        "service": "course-service",
        "version": APP_VERSION,
        "pod": POD_NAME
    }


@app.get("/live")
def liveness():
    return {
        "service": "course-service",
        "status": "alive",
        "pod": POD_NAME
    }


@app.get("/ready")
def readiness():
    try:
        with db() as connection:
            connection.execute("SELECT 1").fetchone()

        return {
            "service": "course-service",
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
        "service": "course-service",
        "status": "healthy",
        "pod": POD_NAME
    }


@app.get("/instance")
def instance():
    return {
        "service": "course-service",
        "version": APP_VERSION,
        "pod": POD_NAME,
        "namespace": POD_NAMESPACE,
        "node": NODE_NAME
    }


@app.get("/version")
def version():
    return {
        "service": "course-service",
        "version": APP_VERSION,
        "pod": POD_NAME
    }


@app.post("/courses", status_code=201)
def create_course(course: CourseCreate):
    with db() as connection:
        row = connection.execute(
            """
            INSERT INTO courses (title, description)
            VALUES (%s, %s)
            RETURNING id, title, description, created_at
            """,
            (
                course.title,
                course.description
            )
        ).fetchone()

        connection.commit()

    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "created_at": row[3]
    }


@app.get("/courses")
def list_courses():
    with db() as connection:
        rows = connection.execute(
            """
            SELECT id, title, description, created_at
            FROM courses
            ORDER BY id
            """
        ).fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]


@app.get("/courses/{course_id}")
def get_course(course_id: int):
    with db() as connection:
        row = connection.execute(
            """
            SELECT id, title, description, created_at
            FROM courses
            WHERE id = %s
            """,
            (course_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "created_at": row[3]
    }
