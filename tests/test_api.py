from datetime import UTC, datetime
from typing import Self

import pytest
from fastapi.testclient import TestClient
from psycopg import Error

import app as api_app


class FakeCursor:
    def __init__(self, rows: list[tuple[int, str, str, datetime]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[tuple[int, str, str, datetime]]:
        return sorted(self.rows, key=lambda item: item[1])


class FakeConnection:
    should_fail = False

    def __init__(self) -> None:
        self.rows: list[tuple[int, str, str, datetime]] = [
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

    def execute(self, query: str) -> FakeCursor:
        return FakeCursor(self.rows)


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
