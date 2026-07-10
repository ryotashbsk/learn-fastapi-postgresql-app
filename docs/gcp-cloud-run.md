# GCP Cloud Run デプロイ手順

FastAPI コンテナを Artifact Registry に push し、Cloud Run で起動する手順。

## 前提

- `gcloud` CLI がインストール済み
- GCP プロジェクトで課金が有効
- Cloud Run / Artifact Registry / Cloud Build API が有効
- PostgreSQL は Cloud SQL for PostgreSQL を利用

この手順の値は環境に合わせて変更。

```bash
PROJECT_ID="your-gcp-project-id"
REGION="asia-northeast1"
SERVICE_NAME="learn-fastapi-postgresql-app"
REPOSITORY="learn-fastapi"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:latest"
CLOUD_SQL_INSTANCE="${PROJECT_ID}:${REGION}:your-postgres-instance"
DATABASE_URL="postgresql://DB_USER:DB_PASSWORD@/DB_NAME?host=/cloudsql/${CLOUD_SQL_INSTANCE}"
```

## 初回設定

```bash
gcloud config set project "${PROJECT_ID}"

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com

gcloud artifacts repositories create "${REPOSITORY}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="FastAPI sample images"
```

## コンテナ build / push

```bash
gcloud builds submit --tag "${IMAGE}" .
```

## Cloud Run へデプロイ

```bash
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances="${CLOUD_SQL_INSTANCE}" \
  --set-env-vars="DATABASE_URL=${DATABASE_URL}"
```

公開しない API にする場合は `--allow-unauthenticated` を外す。

## 動作確認

```bash
SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format='value(status.url)')"

curl "${SERVICE_URL}/health"
curl "${SERVICE_URL}/items"
```

`/health` が `{"status":"ok","database":"connected"}` を返せば、Cloud Run から PostgreSQL へ接続できている。

## Cloud SQL の初期データ

Cloud SQL の DB に `postgres-init/001-items.sql` を投入。

```bash
gcloud sql connect your-postgres-instance --user=DB_USER --database=DB_NAME
```

接続後に `postgres-init/001-items.sql` の SQL を実行。

## 注意点

- `DATABASE_URL` には実パスワードが含まれるため、運用では Secret Manager 経由の環境変数を推奨
- Cloud Run は `PORT` 環境変数をコンテナへ渡すため、Dockerfile は `${PORT:-8080}` を利用
- Cloud SQL へ接続する Cloud Run サービスアカウントには Cloud SQL Client ロールが必要
