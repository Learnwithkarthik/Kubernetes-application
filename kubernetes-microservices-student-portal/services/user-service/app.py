import os
import socket
import time
from contextlib import contextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr


app = FastAPI(
    title="User Service",
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


class UserCreate(BaseModel):
    name: str
    email: EmailStr


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
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(120) NOT NULL,
                        email VARCHAR(200) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                connection.commit()

            print(
                f"Database initialized successfully "
                f"pod={POD_NAME} version={APP_VERSION}"
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
        "message": "User Service is running",
        "service": "user-service",
        "version": APP_VERSION,
        "pod": POD_NAME
    }


@app.get("/live")
def liveness():
    """
    Liveness checks only whether the application process is running.
    It does not check PostgreSQL.
    """
    return {
        "service": "user-service",
        "status": "alive",
        "pod": POD_NAME
    }


@app.get("/ready")
def readiness():
    """
    Readiness checks whether the application can reach PostgreSQL.
    """
    try:
        with db() as connection:
            connection.execute("SELECT 1").fetchone()

        return {
            "service": "user-service",
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
        "service": "user-service",
        "status": "healthy",
        "pod": POD_NAME
    }


@app.get("/instance")
def instance():
    """
    Shows which Kubernetes Pod handled the request.
    """
    return {
        "service": "user-service",
        "version": APP_VERSION,
        "pod": POD_NAME,
        "namespace": POD_NAMESPACE,
        "node": NODE_NAME
    }


@app.get("/version")
def version():
    return {
        "service": "user-service",
        "version": APP_VERSION,
        "pod": POD_NAME
    }


@app.post("/users", status_code=201)
def create_user(user: UserCreate):
    try:
        with db() as connection:
            row = connection.execute(
                """
                INSERT INTO users (name, email)
                VALUES (%s, %s)
                RETURNING id, name, email, created_at
                """,
                (user.name, user.email)
            ).fetchone()

            connection.commit()

        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "created_at": row[3]
        }

    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )


@app.get("/users")
def list_users():
    with db() as connection:
        rows = connection.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]


@app.get("/users/{user_id}")
def get_user(user_id: int):
    with db() as connection:
        row = connection.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "created_at": row[3]
    }
