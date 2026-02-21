# last-fm-twitter

Last.fm の聴取履歴をもとにランキング画像を生成し、Discord に投稿する Lambda プロジェクト。

- **必要環境:** [uv](https://docs.astral.sh/uv/) と Python 3.13
- **デプロイ手順:** [DEPLOY.md](DEPLOY.md) を参照

## セットアップ

```bash
uv sync
```

開発時にテストや Lint を回す場合は:

```bash
uv sync --extra dev
```

### コマンド

dev 依存（`uv sync --extra dev`）を入れたあと、[invoke](https://www.pyinvoke.org/) で次を実行する（uv で一緒にインストールされるため、別途ツールのインストールは不要）。

```bash
uv run inv lint    # ruff format のあと ruff check --fix
uv run inv test    # pytest
uv run inv check   # lint のあと test を一括実行
uv run inv --list  # 利用可能なタスク一覧
```

## テストのやり方

### テストの実行

`uv run inv test` でテストを実行する。lint と test をまとめて回す場合は `uv run inv check`。

### 画像処理のテストについて

`tests/test_draw_ranking.py` は、Last.fm API をモックしたフィクスチャで画像を実際に生成し、正解画像とピクセル比較するテストです。Lambda にデプロイせずに画像処理の変更を検証できます。

**前提:**  
画像テストを実行するには、リポジトリ直下に `fonts/` を用意し、main.py の FONT1〜FONT5 と同じフォント（`azuki.ttf`, `Ronde-B_square.otf`, `851letrogo_007.ttf`, `logotypejp_mp_b_1.1.ttf`, `logotypejp_mp_m_1.1.ttf`）を置く必要があります。フォントや正解画像が無い環境では、画像テストはスキップされます。

**レイアウトやフォントを変えたとき:**  
正解画像を差し替えるには、`fonts/` を用意したうえで `uv run python scripts/generate_expected_image.py` を実行し、生成された `tests/fixtures/expected_ranking_7day.png` をコミットしてください。
