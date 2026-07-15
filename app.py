import os
from datetime import datetime
from typing import ClassVar

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, Session, SQLModel, create_engine, select

load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://sample_user:sample_password@localhost:5432/sample_app',
)
ENGINE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
engine = create_engine(ENGINE_URL)

app = FastAPI(title='FastAPI + PostgreSQL')


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str


class Item(SQLModel, table=True):
    __tablename__: ClassVar[str] = 'items'

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ''
    created_at: datetime | None = None


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


def get_session() -> Session:
    return Session(engine)


def serialize_item(item: Item) -> ItemResponse:
    return ItemResponse(
        id=str(item.id),
        name=item.name,
        description=item.description,
        created_at=item.created_at.isoformat()
        if isinstance(item.created_at, datetime)
        else None,
    )


def fetch_item_or_404(session: Session, item_id: int) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')

    return item


@app.get('/', response_model=MessageResponse)
def index() -> MessageResponse:
    return MessageResponse(message='Hello FastAPI + PostgreSQL')


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse | JSONResponse:
    try:
        with get_session() as session:
            session.connection()

        return HealthResponse(status='ok', database='connected')
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=500,
            content={'status': 'error', 'detail': str(exc)},
        )


@app.get('/items', response_model=ItemsResponse)
def get_items() -> ItemsResponse:
    with get_session() as session:
        items = session.exec(select(Item).order_by(Item.name)).all()

    return ItemsResponse(items=[serialize_item(item) for item in items])


@app.post('/items', response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreateRequest) -> ItemResponse:
    item = Item(name=payload.name, description=payload.description)

    with get_session() as session:
        session.add(item)
        session.commit()
        session.refresh(item)

    return serialize_item(item)


@app.get('/items/{item_id}', response_model=ItemResponse)
def get_item(item_id: int) -> ItemResponse:
    with get_session() as session:
        return serialize_item(fetch_item_or_404(session, item_id))


@app.put('/items/{item_id}', response_model=ItemResponse)
def update_item(item_id: int, payload: ItemUpdateRequest) -> ItemResponse:
    with get_session() as session:
        item = fetch_item_or_404(session, item_id)
        item.name = payload.name
        item.description = payload.description
        session.add(item)
        session.commit()
        session.refresh(item)

    return serialize_item(item)


@app.delete('/items/{item_id}', response_model=DeleteResponse)
def delete_item(item_id: int) -> DeleteResponse:
    with get_session() as session:
        item = fetch_item_or_404(session, item_id)
        session.delete(item)
        session.commit()

    return DeleteResponse(message='Item deleted')
