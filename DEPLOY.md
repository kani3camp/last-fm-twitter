# Lambda デプロイ手順（Python 3.13）

**前提:** [uv](https://docs.astral.sh/uv/) がインストールされていること。依存関係は `pyproject.toml` + `uv.lock` で管理。

## 1. レイヤーをビルド（ローカル）

```bash
uv run python build_lambda_layer.py
```

→ `layer.zip` が生成される。**Lambda は Linux で動くため、`--python-platform linux` で Linux 用のパッケージ（Pillow の C 拡張など）を取得している。** Windows でビルドしてもそのまま Lambda で使える。

Chart 画像への移行では文字組み用の `uharfbuzz` を追加しているため、関数コードより先にこの新しいレイヤーを用意してください。従来のレイヤーのまま関数ZIPだけを更新すると、依存パッケージが不足します。

## 2. AWS Lambda レイヤーを更新

1. **AWS コンソール** → **Lambda** → **レイヤー**
2. 既存のレイヤーを編集するか、新規作成
3. **アップロード** で `layer.zip` をアップロード
4. **互換性のあるランタイム** に **Python 3.13** を選択して保存

## 3. Lambda 関数を Python 3.13 に更新

1. **Lambda** → 対象の関数を開く
2. **設定** → **一般設定** → **編集**
3. **ランタイム** を **Python 3.13** に変更して保存
4. **設定** → **レイヤー** で、手順 2 で更新したレイヤーがアタッチされていることを確認（なければ追加）

## 4. 関数コードを更新

1. ローカルで以下を実行すると `function.zip` が生成される（AWS には接続しない）：

   ```bash
   uv run python scripts/build_function.py
   ```

2. `function.zip` には `main.py`、`ranking_image.py`、`assets/fonts/`（フォントとライセンス）が入る。
   `.env`、API キー、Webhook URL は含めない。依存パッケージは従来どおりレイヤーを使用する。
3. デプロイする際は **コード** → **アップロード元** → **.zip ファイル** からこの ZIP をアップロードする。
   `main.py` だけのコピー＆ペーストでは、新しい描画モジュールとフォントが不足する。
4. **ランタイム設定** のハンドラを `main.lambda_handler` に設定する。

## 5. 環境変数・S3

- **LASTFM_API_KEY**
- **DISCORD_WEBHOOK_URL**
- 新しい画像のフォントは関数 ZIP の `assets/fonts/` に同梱する。従来の S3 の `fonts/` は使用しない。
- ローカル検証のみ行う場合は [README.md](README.md) のプレビューを使用する。Lambda テストや `main.py` の直接実行は Discord へ実投稿する。

## 6. 動作確認

- **テスト** タブでイベントを送って実行できる
- スケジュール（日曜 / 1日 / 12月30日）では引数なしで自動実行される

### テスト用イベント（period 指定）

ランキングを強制実行したいときは、テストイベントの JSON で `period` を指定する。

```json
{
  "period": "7day"
}
```

| `period`    | 内容     |
|------------|----------|
| `"7day"`   | 今週     |
| `"1month"` | 先月     |
| `"12month"`| 今年     |

指定がない場合は従来どおり、日付に応じてのみ実行される（日曜 / 1日 / 12月30日）。
