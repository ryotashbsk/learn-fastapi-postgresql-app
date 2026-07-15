from datetime import UTC, datetime
from typing import Self

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import app as api_app


class FakeResult:
    def __init__(self, items: list[api_app.Item]) -> None:
        self.items = items

    def all(self) -> list[api_app.Item]:
        return sorted(self.items, key=lambda item: item.name)


class FakeSession:
    should_fail = False

    def __init__(self) -> None:
        self.items: list[api_app.Item] = [
            api_app.Item(
                id=1,
                name='Banana',
                description='Initial banana',
                created_at=datetime(2026, 1, 2, tzinfo=UTC),
            ),
            api_app.Item(
                id=2,
                name='Apple',
                description='Initial apple',
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ]

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        return None

    def connection(self) -> None:
        if self.should_fail:
            raise SQLAlchemyError('ping failed')

    def exec(self, statement: object) -> FakeResult:
        return FakeResult(self.items)

    def get(self, model: type[api_app.Item], item_id: int) -> api_app.Item | None:
        return next((item for item in self.items if item.id == item_id), None)

    def add(self, item: api_app.Item) -> None:
        if item.id is not None:
            return

        next_id = max(existing_item.id or 0 for existing_item in self.items) + 1
        item.id = next_id
        item.created_at = datetime(2026, 1, 3, tzinfo=UTC)
        self.items.append(item)

    def commit(self) -> None:
        return None

    def refresh(self, item: api_app.Item) -> None:
        return None

    def delete(self, item: api_app.Item) -> None:
        self.items = [
            existing_item for existing_item in self.items if existing_item.id != item.id
        ]


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    fake_session: FakeSession,
) -> TestClient:
    def get_fake_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(api_app, 'get_session', get_fake_session)

    return TestClient(api_app.app)


def test_index(client: TestClient) -> None:
    response = client.get('/')

    assert response.status_code == 200
    assert response.json() == {'message': 'Hello FastAPI + PostgreSQL'}


def test_health(client: TestClient) -> None:
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'connected'}


def test_health_error(
    client: TestClient,
    fake_session: FakeSession,
) -> None:
    fake_session.should_fail = True

    response = client.get('/health')

    assert response.status_code == 500
    assert response.json() == {'status': 'error', 'detail': 'ping failed'}


def test_get_items(client: TestClient) -> None:
    response = client.get('/items')

    assert response.status_code == 200
    assert response.json() == {
        'items': [
            {
                'id': '2',
                'name': 'Apple',
                'description': 'Initial apple',
                'created_at': '2026-01-01T00:00:00+00:00',
            },
            {
                'id': '1',
                'name': 'Banana',
                'description': 'Initial banana',
                'created_at': '2026-01-02T00:00:00+00:00',
            },
        ]
    }


def test_get_item(client: TestClient) -> None:
    response = client.get('/items/1')

    assert response.status_code == 200
    assert response.json() == {
        'id': '1',
        'name': 'Banana',
        'description': 'Initial banana',
        'created_at': '2026-01-02T00:00:00+00:00',
    }


def test_get_item_not_found(client: TestClient) -> None:
    response = client.get('/items/999')

    assert response.status_code == 404
    assert response.json() == {'detail': 'Item not found'}


def test_create_item(client: TestClient) -> None:
    response = client.post(
        '/items',
        json={'name': 'Cherry', 'description': 'Created item'},
    )

    assert response.status_code == 201
    assert response.json() == {
        'id': '3',
        'name': 'Cherry',
        'description': 'Created item',
        'created_at': '2026-01-03T00:00:00+00:00',
    }


def test_update_item(client: TestClient) -> None:
    response = client.put(
        '/items/1',
        json={'name': 'Blueberry', 'description': 'Updated item'},
    )

    assert response.status_code == 200
    assert response.json() == {
        'id': '1',
        'name': 'Blueberry',
        'description': 'Updated item',
        'created_at': '2026-01-02T00:00:00+00:00',
    }


def test_update_item_not_found(client: TestClient) -> None:
    response = client.put(
        '/items/999',
        json={'name': 'Blueberry', 'description': 'Updated item'},
    )

    assert response.status_code == 404
    assert response.json() == {'detail': 'Item not found'}


def test_delete_item(client: TestClient) -> None:
    response = client.delete('/items/1')

    assert response.status_code == 200
    assert response.json() == {'message': 'Item deleted'}

    get_response = client.get('/items/1')
    assert get_response.status_code == 404


def test_delete_item_not_found(client: TestClient) -> None:
    response = client.delete('/items/999')

    assert response.status_code == 404
    assert response.json() == {'detail': 'Item not found'}
