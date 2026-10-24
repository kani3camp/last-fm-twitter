# last-fm-twitter

Last.fm の聴取履歴からランキング画像を生成し、Discord に投稿する Python / Lambda プロジェクト。

## ローカルで画像を確認

Python の必要バージョンは `pyproject.toml` を参照してください。

```sh
uv sync --extra dev
uv run python scripts/preview_ranking.py --output preview.png
uv run python scripts/preview_ranking.py --count 6 --output preview-6.png
uv run python scripts/preview_ranking.py --count 1 --output preview-1.png
uv run python scripts/preview_ranking.py --random-background --output preview-random.png
uv run python scripts/preview_ranking.py --background '#202040' --output preview-dark.png
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
- API の期間指定（`7day`／`1month`／`12month`）を維持し、画像と投稿文は「過去7日間／過去1か月／過去12か月」に統一します。日付は全期間で `AS OF` と取得日を表示し、API が返さない正確な集計開始・終了時刻やカレンダー上の月・年を断定しません。実行日・スケジュール判定は呼び出しごとにJSTで取得します。
- フォントとライセンスは `assets/fonts/` に同梱します。画像生成時にフォントをダウンロードする必要はありません。
- 通常の投稿画像は従来どおり、生成のたびにRGB各値0〜255から背景色をランダムに選びます。背景上の見出し・出典の文字色は読みやすさに応じて調整し、白いカード内の配色は維持します。プレビュー／参照比較は水色固定が既定で、`--random-background` または `--background` で色を変えて確認できます。

## 検証

```sh
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check .
uv run python scripts/build_function.py
```

10曲／6曲の画像回帰テストは `tests/fixtures/chart_10.png` と `chart_6.png` を比較します。Pillow／FreeTypeの環境差を許容するため、ヘッダー・1位・2〜3位・4〜10位・フッターの各領域でRGB各チャンネルの平均誤差2.0/255未満を要求します。配置・期間表記・文字の収まり・バー比率は別のテストで検証します。デザイン変更で期待画像を更新する場合は、プレビューを確認したうえで以下を実行してください。通常のテストは期待画像を更新しません。

`reference_chart_10.png` と `reference_chart_6.png` は参照アートボードを1000×2000で書き出した原本です。こちらは書き換えず、ブラウザーとPillowの文字輪郭の描画差を許容した比較（RGB各チャンネルの平均誤差2.2/255未満）にも使用します。正確さのため変更した期間・取得日・見出しの3領域だけをこの原本比較から除外し、原本と比較する領域を `scripts/image_comparison.py` に明記しています。文字間隔は HarfBuzz で計算し、Windows／Linuxで共通にしています。

```sh
uv run python scripts/preview_ranking.py --output tests/fixtures/chart_10.png
uv run python scripts/preview_ranking.py --count 6 --output tests/fixtures/chart_6.png
```

`main.py` は実サービスへアクセスし通知を投稿するため、プレビューには使用しません。配布方法は [DEPLOY.md](DEPLOY.md) を参照してください。

## Linux / Lambda互換環境でのローカル検証

描画は2倍解像度から縮小します。3倍描画は128MiB制限のローカル連続実行でOOMを再現したため使用しません。GitHub Actionsの [Validate](.github/workflows/validate.yml) はLinuxでのテストに加え、AWS公式Lambda Pythonイメージで、ネットワークを無効にした128MiB・x86_64のハンドラスモークテストも実行します。

ローカルで同じ検証を行うにはDockerを用意し、以下を実行します。PowerShellでは `$PWD` を適切な絶対パスに置き換えることもできます。

```sh
uv run python build_lambda_layer.py
docker run --rm --platform linux/amd64 --network none --memory 128m --memory-swap 128m --cpus 1 --read-only --tmpfs /tmp:rw,size=64m --volume "$PWD:/var/task:ro" -e PYTHONPATH=/var/task/layer/python/lib/python3.13/site-packages --entrypoint /var/lang/bin/python3.13 public.ecr.aws/lambda/python@sha256:e0237850eecd760896365e768bac1526ea01098e325fa590e5bc735b26d5dbb9 scripts/profile_renderer.py
```

`profile_renderer.py` はAPI取得とDiscord送信をモックし、3期間×1／6／10曲の計9回を同じプロセスで実行します。実投稿をせず、画像寸法、ピークRSS、cgroup上限・最大使用量を出力します。RSSとcgroup計測は別指標です。このコンテナーテストはAWS実機の検証を代替しません。実環境のリリース条件は `DEPLOY.md` を参照してください。
