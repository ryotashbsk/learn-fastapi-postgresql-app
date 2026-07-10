# Flask と FastAPI の比較

## 結論

型定義、OpenAPI 自動生成、非同期処理との相性を重視する API 開発では FastAPI が向く。  
最小構成で自由度高く作る小規模アプリや、既存 Flask 資産を活かす場合は Flask が向く。

このリポジトリは PostgreSQL から JSON を返す API サンプルのため、レスポンス型を明示できる FastAPI との相性が良い。

## 比較表

| 観点 | Flask | FastAPI |
| --- | --- | --- |
| 基本思想 | 小さな Web フレームワーク | API 開発向けフレームワーク |
| 実装スタイル | 関数ルーティング中心 | 型定義とルーティング中心 |
| 型定義 | 標準では必須ではない | Pydantic による型定義が中心 |
| リクエスト検証 | 自前実装または拡張機能 | 型定義から自動検証 |
| レスポンス定義 | `jsonify()` や `dict` で返却 | `response_model` で明示可能 |
| API ドキュメント | 拡張機能が必要 | OpenAPI / Swagger UI を自動生成 |
| 非同期処理 | 対応可能だが主軸ではない | `async def` を標準的に扱える |
| 学習コスト | 低い | 型定義と Pydantic の理解が必要 |
| 自由度 | 高い | API 設計の型に寄せる書き方 |
| エコシステム | 歴史が長く情報が多い | API 開発用途で採用が増加 |
| 運用サーバー | WSGI サーバーが基本 | ASGI サーバーが基本 |

## Flask のメリット

- 最小構成で始めやすい
- 書き方がシンプルで学習しやすい
- 拡張機能が多く、用途に合わせて選べる
- 既存情報や運用事例が多い
- 小規模な管理画面、簡単な Web アプリ、プロトタイプに向く

## Flask のデメリット

- リクエストやレスポンスの型定義は標準では弱い
- OpenAPI ドキュメント生成には追加設定や拡張機能が必要
- 入力値検証やエラーレスポンスの形式が実装者に依存しやすい
- API が増えるほど、スキーマ管理を別途考える必要がある
- 非同期処理を主軸にした設計では FastAPI より扱いにくい場合がある

## FastAPI のメリット

- 型定義からリクエスト検証とレスポンススキーマを扱える
- OpenAPI / Swagger UI が自動生成される
- API の入出力仕様がコード上で明確になる
- Pydantic により JSON API のデータ構造を表現しやすい
- `async def` による非同期処理と相性が良い
- クライアントや外部連携向け API の保守性を高めやすい

## FastAPI のデメリット

- Pydantic のモデル定義を理解する必要がある
- 小さな用途では Flask より記述量が増える場合がある
- 型定義を雑に扱うと、FastAPI の利点が薄くなる
- ASGI、Pydantic、依存性注入など、周辺概念の学習が必要
- HTML 中心の Web アプリでは、API 特化の利点を活かしきれない場合がある

## 書き方の違い

Flask は戻り値を `dict` や `jsonify()` で返す書き方が中心。

```python
@app.get('/items')
def get_items():
    return jsonify({'items': items})
```

FastAPI は Pydantic model でレスポンス型を定義し、`response_model` に指定できる。

```python
class ItemsResponse(BaseModel):
    items: list[ItemResponse]


@app.get('/items', response_model=ItemsResponse)
def get_items() -> ItemsResponse:
    return ItemsResponse(items=items)
```

## このリポジトリで FastAPI が向く理由

- JSON API のみを提供している
- `/items` のレスポンス構造を型で表現できる
- OpenAPI により API 仕様を自動確認できる
- PostgreSQL の行データをレスポンス用の型へ変換する処理を明示できる
- 将来 POST / PUT / DELETE を追加する場合、入力値検証を Pydantic model に寄せられる

## Flask を選ぶ判断

- とにかく最小構成で動くものを作りたい
- API 仕様書や型定義を重視しない
- 既存の Flask 資産が多い
- HTML テンプレート中心の小規模 Web アプリ
- チームが Flask に慣れている

## FastAPI を選ぶ判断

- JSON API を中心に開発する
- 入出力の型を明確にしたい
- OpenAPI / Swagger UI を自動生成したい
- フロントエンドや外部システムと API 仕様を共有したい
- 将来的に非同期処理や複数エンドポイントの拡張を想定している

## まとめ

Flask は自由度と簡潔さが強み。  
FastAPI は型定義、検証、API ドキュメント生成が強み。

このリポジトリでは JSON API としての保守性を優先するため、FastAPI への置き換えは妥当な選択。
