import os
from datetime import datetime
from typing import Sequence

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
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


class ItemCreateRequest(BaseModel):
    name: str
    description: str = ''


class ItemUpdateRequest(BaseModel):
    name: str
    description: str


class ItemsResponse(BaseModel):
    items: list[ItemResponse]


class DeleteResponse(BaseModel):
    message: str


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


def fetch_item_or_404(
    connection: psycopg.Connection[TupleRow], item_id: int
) -> ItemResponse:
    row = connection.execute(
        """
        SELECT id, name, description, created_at
        FROM items
        WHERE id = %s
        """,
        (item_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail='Item not found')

    return serialize_item(row)


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


@app.post('/items', response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreateRequest) -> ItemResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            INSERT INTO items (name, description)
            VALUES (%s, %s)
            RETURNING id, name, description, created_at
            """,
            (payload.name, payload.description),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail='Item creation failed')

    return serialize_item(row)


@app.get('/items/{item_id}', response_model=ItemResponse)
def get_item(item_id: int) -> ItemResponse:
    with get_connection() as connection:
        return fetch_item_or_404(connection, item_id)


@app.put('/items/{item_id}', response_model=ItemResponse)
def update_item(item_id: int, payload: ItemUpdateRequest) -> ItemResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            UPDATE items
            SET name = %s,
                description = %s
            WHERE id = %s
            RETURNING id, name, description, created_at
            """,
            (payload.name, payload.description, item_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail='Item not found')

    return serialize_item(row)


@app.delete('/items/{item_id}', response_model=DeleteResponse)
def delete_item(item_id: int) -> DeleteResponse:
    with get_connection() as connection:
        row = connection.execute(
            """
            DELETE FROM items
            WHERE id = %s
            RETURNING id
            """,
            (item_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail='Item not found')

    return DeleteResponse(message='Item deleted')
