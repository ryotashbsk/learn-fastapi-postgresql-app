import os
from datetime import datetime
from typing import Sequence

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from psycopg.rows import TupleRow
from pydantic import BaseModel

load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://sample_user:sample_password@localhost:5432/sample_app',
)

app = FastAPI(title='FastAPI + PostgreSQL')


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str


class ItemResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str | None


class ItemsResponse(BaseModel):
    items: list[ItemResponse]


def get_connection() -> psycopg.Connection[TupleRow]:
    return psycopg.connect(DATABASE_URL)


def serialize_item(item: Sequence[object]) -> ItemResponse:
    created_at = item[3]

    return ItemResponse(
        id=str(item[0]),
        name=str(item[1]),
        description=str(item[2]),
        created_at=created_at.isoformat() if isinstance(created_at, datetime) else None,
    )


@app.get('/', response_model=MessageResponse)
def index() -> MessageResponse:
    return MessageResponse(message='Hello FastAPI + PostgreSQL')


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse | JSONResponse:
    try:
        with get_connection() as connection:
            connection.execute('SELECT 1')

        return HealthResponse(status='ok', database='connected')
    except psycopg.Error as exc:
        return JSONResponse(
            status_code=500,
            content={'status': 'error', 'detail': str(exc)},
        )


@app.get('/items', response_model=ItemsResponse)
def get_items() -> ItemsResponse:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, description, created_at
            FROM items
            ORDER BY name ASC
            """
        ).fetchall()

    return ItemsResponse(items=[serialize_item(row) for row in rows])
