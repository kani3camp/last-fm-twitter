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

## テストのやり方

### テストの実行

プロジェクトルートで以下を実行する。

```bash
uv run pytest tests/ -v
```

初回や `pyproject.toml` の依存を変えたあとは、先に `uv sync --extra dev` で dev 依存を入れておく。

### 画像処理のテストについて

`tests/test_draw_ranking.py` は、Last.fm API をモックしたフィクスチャで画像を実際に生成し、正解画像とピクセル比較するテストです。Lambda にデプロイせずに画像処理の変更を検証できます。

**前提:**  
画像テストを実行するには、リポジトリ直下に `fonts/` を用意し、main.py の FONT1〜FONT5 と同じフォント（`azuki.ttf`, `Ronde-B_square.otf`, `851letrogo_007.ttf`, `logotypejp_mp_b_1.1.ttf`, `logotypejp_mp_m_1.1.ttf`）を置く必要があります。フォントや正解画像が無い環境では、画像テストはスキップされます。

**レイアウトやフォントを変えたとき:**  
正解画像を差し替えるには、`fonts/` を用意したうえで `uv run python scripts/generate_expected_image.py` を実行し、生成された `tests/fixtures/expected_ranking_7day.png` をコミットしてください。

### 画像テストだけ実行する場合

```bash
uv run pytest tests/test_draw_ranking.py -v
```

スキップ理由を確認したいときは `-rs` を付ける。

```bash
uv run pytest tests/test_draw_ranking.py -v -rs
```
