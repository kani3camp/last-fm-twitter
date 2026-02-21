# Lambda デプロイ手順（Python 3.13）

**前提:** [uv](https://docs.astral.sh/uv/) がインストールされていること。依存関係は `pyproject.toml` + `uv.lock` で管理。

## 1. レイヤーをビルド（ローカル）

```bash
uv run python build_lambda_layer.py
```

→ `layer.zip` が生成される。**Lambda は Linux で動くため、`--python-platform linux` で Linux 用のパッケージ（Pillow の C 拡張など）を取得している。** Windows でビルドしてもそのまま Lambda で使える。

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

1. **コード** タブで、以下を手動でコピー＆ペースト：
   - `main.py` の内容を **lambda_function.py**（またはメインハンドラのファイル）に貼り付け
   - `utils.py` の内容を **utils.py** として同じ関数内に追加（新規ファイル作成）

2. **ハンドラ** が `lambda_function.lambda_handler` の場合は、`main.py` のハンドラ名に合わせて  
   **ランタイム設定** のハンドラを `main.lambda_handler` に変更する。

## 5. 環境変数・S3

- **LASTFM_API_KEY**
- **DISCORD_WEBHOOK_URL**
- フォントは従来どおり S3 バケット `last-fm-twitter` の `fonts/` に配置されている前提

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

---

## 画像処理のローカルテスト

画像処理だけを Lambda にデプロイせずに検証したい場合は、ローカルで pytest を実行する。

- **実行:** プロジェクトルートで `uv run pytest tests/test_draw_ranking.py -v`（要 `uv sync --extra dev`）
- **前提:** `fonts/` に次のフォントを配置すること（main.py の FONT1〜FONT5 と同一）  
  `azuki.ttf`, `Ronde-B_square.otf`, `851letrogo_007.ttf`, `logotypejp_mp_b_1.1.ttf`, `logotypejp_mp_m_1.1.ttf`
- **正解画像の初回生成・更新:** 上記フォントを配置したうえで  
  `uv run python scripts/generate_expected_image.py` を実行すると、  
  `tests/fixtures/expected_ranking_7day.png` が生成される。レイアウトを変えたあとはこのスクリプトを再実行して正解画像を更新し、コミットする。
