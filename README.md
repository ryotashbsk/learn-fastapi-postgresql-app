# FastAPI + PostgreSQL

FastAPI から PostgreSQL の `items` table を読み取る JSON API サンプル。

- フレームワーク: FastAPI
- ORM: SQLModel
- DB driver: psycopg
- ASGI サーバー: uvicorn
- Python 管理: uv
- ローカル DB: Docker Compose PostgreSQL

## 前提

| ツール | 用途 |
| --- | --- |
| uv | Python と仮想環境、依存パッケージの管理 |
| Docker Compose | ローカル PostgreSQL の起動 |
| psql または GUI クライアント | PostgreSQL のデータ確認 |

## ファイル構成

```txt
learn-fastapi-postgresql-app/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── docker-compose.yml
├── cloudbuild.yaml
├── postgres-init/
│   └── 001-items.sql
├── docs/
│   ├── gcp-cloud-run.md
│   └── flask-vs-fastapi.md
├── .vscode/
│   ├── launch.json
│   ├── settings.json
│   ├── extensions.json
│   └── tasks.json
├── .env.example
├── Dockerfile
└── README.md
```

## エンドポイント

| メソッド | URL | 概要 |
| --- | --- | --- |
| GET | `http://localhost:8080/` | アプリのメッセージ |
| GET | `http://localhost:8080/health` | PostgreSQL への接続状態 |
| GET | `http://localhost:8080/items` | `items` table のデータ |
| POST | `http://localhost:8080/items` | `items` table へデータを追加 |
| GET | `http://localhost:8080/items/{id}` | `items` table の単体データ |
| PUT | `http://localhost:8080/items/{id}` | `items` table のデータを更新 |
| DELETE | `http://localhost:8080/items/{id}` | `items` table のデータを削除 |

## Python 設定

`pyproject.toml` は Ruff、ty、pytest、coverage の設定ファイル。

| 設定 | 内容 |
| --- | --- |
| `tool.ruff.lint.ignore` | このサンプルでの Ruff ルール無視対象 |
| `tool.ruff.format.quote-style` | 文字列引用符を single quote に統一 |
| `tool.ty.environment.python-version` | 型チェック対象の Python バージョン |
| `tool.ty.src.include` | 型チェック対象 |
| `tool.pytest.ini_options.testpaths` | pytest のテスト探索対象 |
| `tool.coverage.run.source` | coverage の計測対象 |

## ローカルセットアップ

### ローカル実行用の環境変数ファイル

```bash
cp .env.example .env
```

### Python 3.11 の仮想環境

```bash
uv venv --python 3.11
```

### `.venv` への依存パッケージ追加

```bash
uv pip install -r requirements.txt
```

### 開発用ツールの追加

```bash
uv pip install -r requirements-dev.txt
```

### PostgreSQL コンテナのバックグラウンド起動

```bash
docker compose up -d postgres
```

### uvicorn による FastAPI アプリ起動

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

VS Code では、実行とデバッグの `FastAPI アプリを起動` を利用。

## 開発用チェック

開発用ツールを追加済みの場合に利用。

### pre-commit hook の有効化

```bash
uv run pre-commit install
```

### 品質チェック一式

```bash
uv run pre-commit run --all-files
```

### コードフォーマット

```bash
uv run ruff format .
```

### lint

```bash
uv run ruff check .
```

### 型チェック

```bash
uv run ty check
```

### テスト

```bash
uv run pytest
```

### カバレッジ

```bash
uv run coverage run -m pytest
uv run coverage report
```

## 動作確認

### FastAPI の Swagger UI

```txt
http://localhost:8080/docs
```

### PostgreSQL への接続状態

```bash
curl http://localhost:8080/health
```

### `items` table のデータ

```bash
curl http://localhost:8080/items
```

返却例:

```json
{
  "items": [
    {
      "id": "1",
      "name": "Apple",
      "description": "FastAPI sample item from PostgreSQL",
      "created_at": "2026-01-01T00:00:00+00:00"
    }
  ]
}
```

### HTTP メソッド別の操作サンプル

作成:

```bash
curl -X POST http://localhost:8080/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"Cherry","description":"Created from POST"}'
```

単体取得:

```bash
curl http://localhost:8080/items/1
```

更新:

```bash
curl -X PUT http://localhost:8080/items/1 \
  -H 'Content-Type: application/json' \
  -d '{"name":"Apple","description":"Updated from PUT"}'
```

削除:

```bash
curl -X DELETE http://localhost:8080/items/1
```

## ローカル PostgreSQL

アプリが使う接続情報:

```txt
URL: postgresql://sample_user:sample_password@localhost:5432/sample_app
Database: sample_app
Table: items
```

psql の接続例:

```bash
psql postgresql://sample_user:sample_password@localhost:5432/sample_app
```

## 初期データ

初期データの定義場所は `postgres-init/001-items.sql`。
PostgreSQL 公式イメージの `/docker-entrypoint-initdb.d` へのマウントにより、`postgres-data` volume が空の初回起動時だけ実行。

既存の `postgres-data` volume がある場合、初期データファイルは自動再実行なし。
再初期化時は volume 削除後に起動。

```bash
docker compose down -v
docker compose up -d postgres
```

## GCP デプロイ設定

Cloud Run、Cloud SQL for PostgreSQL、Artifact Registry、Secret Manager を使った構成。
GitHub push 時の自動再デプロイは Cloud Build trigger と `cloudbuild.yaml` を使う。

詳細な設定値、build / deploy、Cloud SQL 初期データ投入、トラブルシュートは [docs/gcp-cloud-run.md](docs/gcp-cloud-run.md) を参照。

主要リソース:

| 種別 | 値 |
| --- | --- |
| Project ID | `learn-fastapi-********` |
| Region | `asia-northeast1` |
| Artifact Registry repository | `learn-fastapi` |
| Cloud Run service | `learn-fastapi-********-git` |
| Container image name | `learn-fastapi-********` |
| Cloud SQL instance | `learn-fastapi-postgres` |
| Secret Manager secret | `database-url` |
| Cloud Run service account | `cloud-run-fastapi@<PROJECT_ID>.iam.gserviceaccount.com` |
| Cloud Build trigger | `deploy-cloud-run-main` |
| Cloud Build trigger region | `asia-northeast1` |
| Cloud Build service account | `cloud-build-deploy@<PROJECT_ID>.iam.gserviceaccount.com` |

プレースホルダー:

| 値 | 内容 |
| --- | --- |
| `********` | 環境固有の識別子部分 |
| `<PROJECT_ID>` | GCP project ID。例: `learn-fastapi-********` |

`main` branch で API 実行に関係するファイルが変わると、Cloud Build trigger が `cloudbuild.yaml` を実行し、Cloud Run を再デプロイする。
`README.md` や `docs/` だけの変更では自動デプロイしない。

手動で再デプロイする場合:

```bash
PROJECT_ID="learn-fastapi-********"
CLOUD_RUN_SERVICE="learn-fastapi-********-git"
RUNTIME_SERVICE_ACCOUNT="cloud-run-fastapi@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_NAME="learn-fastapi-********"
IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/learn-fastapi/${IMAGE_NAME}:latest"

gcloud builds submit \
  --project="${PROJECT_ID}" \
  --tag "${IMAGE}" \
  .

gcloud run services update "${CLOUD_RUN_SERVICE}" \
  --project="${PROJECT_ID}" \
  --region=asia-northeast1 \
  --image="${IMAGE}" \
  --service-account="${RUNTIME_SERVICE_ACCOUNT}"
```
