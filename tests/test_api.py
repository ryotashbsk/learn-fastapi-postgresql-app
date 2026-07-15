from datetime import UTC, datetime
from typing import Self, Sequence

import pytest
from fastapi.testclient import TestClient
from psycopg import Error

import app as api_app

ItemRow = tuple[int, str, str, datetime]
DeletedItemRow = tuple[int]


class FakeCursor:
    def __init__(self, rows: list[ItemRow] | list[DeletedItemRow]) -> None:
        self.rows = rows

    def fetchall(self) -> list[ItemRow]:
        item_rows = [row for row in self.rows if len(row) == 4]
        return sorted(item_rows, key=lambda item: item[1])

    def fetchone(self) -> ItemRow | DeletedItemRow | None:
        if len(self.rows) == 0:
            return None

        return self.rows[0]


class FakeConnection:
    should_fail = False

    def __init__(self) -> None:
        self.rows: list[ItemRow] = [
            (1, 'Banana', 'Initial banana', datetime(2026, 1, 2, tzinfo=UTC)),
            (2, 'Apple', 'Initial apple', datetime(2026, 1, 1, tzinfo=UTC)),
        ]

    def __enter__(self) -> Self:
        if self.should_fail:
            raise Error('ping failed')

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        return None

    def execute(
        self,
        query: str,
        params: Sequence[object] | None = None,
    ) -> FakeCursor:
        normalized_query = ' '.join(query.split())

        if normalized_query == 'SELECT 1':
            return FakeCursor([])

        if normalized_query.startswith(
            'SELECT id, name, description, created_at FROM items WHERE id = %s'
        ):
            item_id = self.get_item_id(params)
            return FakeCursor([row for row in self.rows if row[0] == item_id])

        if normalized_query.startswith('INSERT INTO items'):
            name, description = self.get_item_payload(params)
            next_id = max(row[0] for row in self.rows) + 1
            row = (next_id, name, description, datetime(2026, 1, 3, tzinfo=UTC))
            self.rows.append(row)
            return FakeCursor([row])

        if normalized_query.startswith('UPDATE items'):
            name, description, item_id = self.get_update_payload(params)
            for index, row in enumerate(self.rows):
                if row[0] == item_id:
                    updated_row = (item_id, name, description, row[3])
                    self.rows[index] = updated_row
                    return FakeCursor([updated_row])

            return FakeCursor([])

        if normalized_query.startswith('DELETE FROM items'):
            item_id = self.get_item_id(params)
            for index, row in enumerate(self.rows):
                if row[0] == item_id:
                    del self.rows[index]
                    return FakeCursor([(item_id,)])

            return FakeCursor([])

        return FakeCursor(self.rows)

    def get_item_id(self, params: Sequence[object] | None) -> int:
        if params is None or not isinstance(params[0], int):
            raise ValueError('item id is required')

        return params[0]

    def get_item_payload(self, params: Sequence[object] | None) -> tuple[str, str]:
        if (
            params is None
            or len(params) != 2
            or not isinstance(params[0], str)
            or not isinstance(params[1], str)
        ):
            raise ValueError('item payload is required')

        return params[0], params[1]

    def get_update_payload(
        self,
        params: Sequence[object] | None,
    ) -> tuple[str, str, int]:
        if (
            params is None
            or len(params) != 3
            or not isinstance(params[0], str)
            or not isinstance(params[1], str)
            or not isinstance(params[2], int)
        ):
            raise ValueError('item update payload is required')

        return params[0], params[1], params[2]


@pytest.fixture
def fake_connection() -> FakeConnection:
    return FakeConnection()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    fake_connection: FakeConnection,
) -> TestClient:
    def get_fake_connection() -> FakeConnection:
        return fake_connection

    monkeypatch.setattr(api_app, 'get_connection', get_fake_connection)

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
    fake_connection: FakeConnection,
) -> None:
    fake_connection.should_fail = True

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
