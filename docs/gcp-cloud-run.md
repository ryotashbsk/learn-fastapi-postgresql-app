# GCP Cloud Run デプロイ手順

FastAPI コンテナを Artifact Registry に push し、Cloud Run で起動する手順。
PostgreSQL は Cloud SQL for PostgreSQL を利用し、DB 接続文字列は Secret Manager から渡す。

## 構成

| 種別 | 値 |
| --- | --- |
| Project ID | `learn-fastapi-postgresql-app` |
| Region | `asia-northeast1` |
| Artifact Registry repository | `learn-fastapi` |
| Cloud Run service | `learn-fastapi-postgresql-app-git` |
| Cloud SQL instance | `learn-fastapi-postgres` |
| Cloud SQL database | `sample_app` |
| Cloud SQL user | `sample_user` |
| Secret Manager secret | `database-url` |
| Cloud Run service account | `cloud-run-fastapi@learn-fastapi-postgresql-app.iam.gserviceaccount.com` |

## 初回設定の流れ

1. GCP プロジェクトで課金を有効化
2. 必要な API を有効化
3. Artifact Registry の Docker repository を作成
4. Cloud SQL for PostgreSQL の instance、database、user を作成
5. Secret Manager に `DATABASE_URL` 用の secret を作成
6. Cloud Run 用の専用サービスアカウントを作成
7. 専用サービスアカウントに必要最小限の IAM ロールを付与
8. Docker image を build して Artifact Registry に push
9. Cloud Run に image、secret、Cloud SQL 接続、サービスアカウントを設定してデプロイ
10. Cloud SQL に初期 SQL を投入

## gcloud 設定

```bash
gcloud config set project learn-fastapi-postgresql-app
gcloud config set run/region asia-northeast1
```

## API 有効化

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com
```

有効化済み API の確認。

```bash
gcloud services list --enabled \
  --project=learn-fastapi-postgresql-app \
  --format="value(config.name)"
```

## Artifact Registry

Docker image の保存先。

```bash
gcloud artifacts repositories create learn-fastapi \
  --project=learn-fastapi-postgresql-app \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Docker repository for learn-fastapi-postgresql-app"
```

現在 Cloud Run が参照する image。

```txt
asia-northeast1-docker.pkg.dev/learn-fastapi-postgresql-app/learn-fastapi/learn-fastapi-postgresql-app:latest
```

`cloud-run-source-deploy` repository は、Cloud Run のソースデプロイで自動作成された未使用 repository だったため削除済み。

## Cloud SQL

PostgreSQL 16 を `asia-northeast1` に作成。
学習用途のため、シングルゾーン構成。

```txt
Instance: learn-fastapi-postgres
Database: sample_app
User: sample_user
Authentication: 組み込み認証
```

Cloud Run から接続する instance connection name。

```txt
learn-fastapi-postgresql-app:asia-northeast1:learn-fastapi-postgres
```

Cloud SQL は `docker-compose.yml` の `/docker-entrypoint-initdb.d` を使わない。
Cloud SQL 作成後に `postgres-init/001-items.sql` を別途実行する必要がある。

## Secret Manager

`DATABASE_URL` は環境変数として直接設定せず、Secret Manager から Cloud Run に渡す。

```txt
Secret name: database-url
Cloud Run env name: DATABASE_URL
Version: latest
```

Secret の値の形式。

```txt
postgresql://sample_user:DB_PASSWORD@/sample_app?host=/cloudsql/learn-fastapi-postgresql-app:asia-northeast1:learn-fastapi-postgres
```

`DB_PASSWORD` は実際の Cloud SQL user password に置き換える。
実パスワードは repository に記載しない。

## IAM

Cloud Run 実行用に専用サービスアカウントを使う。

```txt
cloud-run-fastapi@learn-fastapi-postgresql-app.iam.gserviceaccount.com
```

必要なロール。

```txt
roles/cloudsql.client
roles/secretmanager.secretAccessor
```

`database-url` の secret 読み取り権限は、専用サービスアカウントだけに付与。

デフォルトサービスアカウントに広い権限を付けず、Cloud Run 実行用の権限は専用サービスアカウントへ集約する。

## Build / Deploy

Artifact Registry へ image を build / push。

```bash
gcloud builds submit \
  --project=learn-fastapi-postgresql-app \
  --tag asia-northeast1-docker.pkg.dev/learn-fastapi-postgresql-app/learn-fastapi/learn-fastapi-postgresql-app:latest \
  .
```

Cloud Run service を image で更新。

```bash
gcloud run services update learn-fastapi-postgresql-app-git \
  --project=learn-fastapi-postgresql-app \
  --region=asia-northeast1 \
  --image=asia-northeast1-docker.pkg.dev/learn-fastapi-postgresql-app/learn-fastapi/learn-fastapi-postgresql-app:latest \
  --service-account=cloud-run-fastapi@learn-fastapi-postgresql-app.iam.gserviceaccount.com
```

Cloud Run には以下も設定。

```txt
Cloud SQL connection:
learn-fastapi-postgresql-app:asia-northeast1:learn-fastapi-postgres

Secret:
DATABASE_URL = database-url:latest

Authentication:
未認証の呼び出しを許可
```

## Cloud SQL 初期データ投入

`postgres-init/001-items.sql` は `CREATE TABLE IF NOT EXISTS` と `ON CONFLICT DO NOTHING` を使うため、同じ SQL を再実行しても初期データは重複しない。

一時 Cloud Run Job を作成。

```bash
gcloud run jobs create init-items-table \
  --project=learn-fastapi-postgresql-app \
  --region=asia-northeast1 \
  --image=asia-northeast1-docker.pkg.dev/learn-fastapi-postgresql-app/learn-fastapi/learn-fastapi-postgresql-app:latest \
  --service-account=cloud-run-fastapi@learn-fastapi-postgresql-app.iam.gserviceaccount.com \
  --set-secrets=DATABASE_URL=database-url:latest \
  --set-cloudsql-instances=learn-fastapi-postgresql-app:asia-northeast1:learn-fastapi-postgres \
  --command=python \
  --args='^|||^-c|||import os, psycopg; sql = open("/app/postgres-init/001-items.sql", encoding="utf-8").read(); conn = psycopg.connect(os.environ["DATABASE_URL"]); conn.execute(sql); conn.commit(); count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]; conn.close(); print(f"initialized items count={count}")'
```

Job を実行。

```bash
gcloud run jobs execute init-items-table \
  --project=learn-fastapi-postgresql-app \
  --region=asia-northeast1 \
  --wait
```

実行ログを確認。

```bash
gcloud logging read \
  'resource.type="cloud_run_job" AND resource.labels.job_name="init-items-table"' \
  --project=learn-fastapi-postgresql-app \
  --limit=20 \
  --format="value(timestamp,severity,textPayload,jsonPayload.message)"
```

以下のように出れば投入済み。

```txt
initialized items count=2
```

一時 Job を削除。

```bash
gcloud run jobs delete init-items-table \
  --project=learn-fastapi-postgresql-app \
  --region=asia-northeast1 \
  --quiet
```

## 動作確認

Cloud Run の URL を確認。

```bash
SERVICE_URL="$(gcloud run services describe learn-fastapi-postgresql-app-git \
  --project=learn-fastapi-postgresql-app \
  --region=asia-northeast1 \
  --format='value(status.url)')"
```

疎通確認。

```bash
curl "${SERVICE_URL}/"
curl "${SERVICE_URL}/health"
curl "${SERVICE_URL}/items"
```

`/health` が以下を返せば Cloud Run から Cloud SQL への接続は成功。

```json
{"status":"ok","database":"connected"}
```

`/items` が以下のように返れば初期データ投入も成功。

```json
{
  "items": [
    {
      "id": "1",
      "name": "Apple",
      "description": "FastAPI sample item from PostgreSQL",
      "created_at": "2026-01-01T00:00:00+00:00"
    },
    {
      "id": "2",
      "name": "Banana",
      "description": "Data from PostgreSQL table",
      "created_at": "2026-01-01T00:00:00+00:00"
    }
  ]
}
```

## トラブルシュート

### placeholder が表示される

`Sorry, this is just a placeholder` が表示される場合、Cloud Run が `gcr.io/cloudrun/placeholder` を実行している。
Artifact Registry に push した image を指定して Cloud Run を更新する。

### Secret Manager の権限エラー

Secret Manager の permission error が出る場合、Cloud Run の実行サービスアカウントを確認する。
専用サービスアカウントを指定し、`roles/secretmanager.secretAccessor` が付与されている状態にする。

```txt
cloud-run-fastapi@learn-fastapi-postgresql-app.iam.gserviceaccount.com
```

### items table が存在しない

`/items` が 500 を返し、Cloud Run ログに以下が出る場合、Cloud SQL に初期 SQL が未投入。

```txt
psycopg.errors.UndefinedTable: relation "items" does not exist
```

`Cloud SQL 初期データ投入` の手順で `items` table を作成する。
