# last-fm-twitter

Last.fm の聴取履歴からランキング画像を生成し、Discord に投稿する Python / Lambda プロジェクト。

## ローカルで画像を確認

Python の必要バージョンは `pyproject.toml` を参照してください。

```sh
uv sync --extra dev
uv run python scripts/preview_ranking.py --output preview.png
uv run python scripts/preview_ranking.py --count 6 --output preview-6.png
uv run python scripts/preview_ranking.py --count 1 --output preview-1.png
uv run python scripts/preview_ranking.py --period 1month --date 2026-08-01 --output preview-month.png
uv run python scripts/preview_ranking.py --period 12month --date 2026-12-30 --output preview-year.png
uv run python scripts/compare_design.py --count 10 --output preview-comparison-10.png
uv run python scripts/compare_design.py --count 6 --output preview-comparison-6.png
```

このプレビューは固定 JSON を読み取るだけで、`.env` の読み込み、Last.fm / AWS へのアクセス、Discord 投稿を行いません。`--data path/to/fixture.json` で Last.fm 形式の別データも使用できます。

`compare_design.py` は参照・生成・強調差分を並べたPNGと平均誤差を出力し、比較基準を超えると非ゼロで終了します。参照の仮ユーザー名に揃えて比較し、通常の投稿画像では実ユーザー名 `SoraraP` を表示します。

## 画像の仕様

[参照デザイン](https://claude.ai/chat/8a2b271d-6ec2-4224-b43e-be4e751a5dc3?artifact=6d1ae2be-5d30-4035-b416-36fe4368ef49) の A Chart をベースにした1000×2000の固定キャンバスです。1〜9曲でも残りの順位は空枠で表示します。0曲のときは従来どおり画像を作成せず、テキスト通知を送ります。

- 集計バッジは表示対象の上位10曲の再生数合計、曲数、主アーティストの種類数です。全聴取履歴の総数ではありません。
- 曲名の `feat.` は加工せず保持します。1〜3位は最大2行、4〜10位とアーティストは1行に収め、収まらない文字は「…」で省略します。
- API の期間指定（7日／1か月／12か月）と既存の投稿文は維持します。週次の日付は参照に合わせ実行日を含む7日間を表示し、月次／年次は `AS OF` と取得日を表示します。API が返さない正確な月・年の開始日は推測しません。
- フォントとライセンスは `assets/fonts/` に同梱します。画像生成時にフォントをダウンロードする必要はありません。

## 検証

```sh
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check .
uv run python scripts/build_function.py
```

10曲／6曲の画像回帰テストは `tests/fixtures/chart_10.png` と `chart_6.png` を比較します。デザイン変更で期待画像を更新する場合は、プレビューを確認したうえで以下を実行してください。通常のテストは期待画像を更新しません。

`reference_chart_10.png` と `reference_chart_6.png` は参照アートボードを1000×2000で書き出した原本です。こちらは書き換えず、ブラウザーとPillowの文字輪郭の描画差を許容した比較（RGB各チャンネルの平均誤差2.2/255未満）にも使用します。空枠の位置・バーの比率・文字の収まりは別のテストで検証します。文字間隔は HarfBuzz で計算し、Windows／Linuxで共通にしています。

```sh
uv run python scripts/preview_ranking.py --output tests/fixtures/chart_10.png
uv run python scripts/preview_ranking.py --count 6 --output tests/fixtures/chart_6.png
```

`main.py` は実サービスへアクセスし通知を投稿するため、プレビューには使用しません。配布方法は [DEPLOY.md](DEPLOY.md) を参照してください。
