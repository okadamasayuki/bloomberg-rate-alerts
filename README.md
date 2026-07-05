# Bloomberg 金利ニュース要約

ブルームバーグの RSS ニュースを定期的にチェックし、**金利に関係するニュース**を
日本語の要約・分析つきで **Webサイト** に自動表示するツールです。

🔗 公開サイト: **https://okadamasayuki.github.io/bloomberg-rate-alerts/**

GitHub Actions が3時間ごとにニュースを取得してページを生成し、GitHub Pages で公開します。
スマホのブラウザから URL を開くだけで最新の金利ニュースが見られます（PC操作・サーバー不要）。

## 主な機能

- 📰 **金利ニュースの自動抽出** — Bloomberg の RSS（markets / economics / politics）から
  金利関連キーワード（`金利` `利上げ` `Fed` `FOMC` `rate hike` など）で記事を抽出
- 🇯🇵 **日本語に自動翻訳** — 英語記事の見出し・要約を日本語化（APIキー不要の無料翻訳。失敗時は原文）
- 📊 **利上げ/利下げ要因の分析** — 各記事について「対象国」「利上げ要因・利下げ要因・中立」を推定し、
  具体的な材料と、なぜその方向に金利が動くのかの**仕組みを含む詳しい理由**を表示
- 🗓 **期間フィルタ** — クイックプリセット（24時間 / 3日 / 7日 / すべて）＋
  **開始日〜終了日の日付指定**で絞り込み
- ♻️ **重複除去** — 複数フィードにまたがる同一記事をまとめる
- 🔁 **自動リトライ** — GitHub Pages の一時的なデプロイ失敗を自動で再試行

金利ニュースが無いときは「新着なし」、選んだ期間に無いときは「この期間に金利ニュースはありません」と表示します。

## 公開の有効化（初回だけ）

1. リポジトリを **Public（公開）** にする
   （Settings → General → Danger Zone → "Change repository visibility"）
   ※ 無料プランの GitHub Pages は公開リポジトリが必要です。コードに秘密情報はありません。
2. **Settings → Pages** で Source を **「GitHub Actions」** に設定
3. **Actions** タブ →「金利ニュースサイトを生成して公開」→ **Run workflow** で初回実行
4. 完了すると上記 URL で公開されます

以降は3時間ごとに自動更新されます（更新頻度は `.github/workflows/site.yml` の cron で変更可能）。

## ローカルで確認

```bash
pip install feedparser python-dotenv
python -m bloomberg_rate_alerts.build_site --demo   # サンプルで site/index.html を生成
python -m bloomberg_rate_alerts.build_site          # 実データで生成
# 生成された site/index.html をブラウザで開く
```

## 構成

```
bloomberg_rate_alerts/
├── build_site.py     サイト生成のエントリーポイント（取得→翻訳→分析→HTML出力）
├── news_fetcher.py   RSS取得・金利フィルタ・重複除去
├── translate.py      見出し・要約の日本語化（無料翻訳、失敗時は原文）
├── analyzer.py       対象国・利上げ/利下げ要因・判断理由の推定
├── site_render.py    レスポンシブなHTMLページ生成（期間・日付フィルタのUIとJS）
├── summarizer.py     要約（Claude任意 / RSS概要フォールバック）
├── sample_data.py    デモ用サンプル記事
├── config.py         環境変数の読み込み
├── main.py / mailer.py / render.py / state.py / webapp.py   メール送信（任意機能）
└── tests/            ユニットテスト
.github/workflows/site.yml   定期実行→GitHub Pages公開
```

## 設定（環境変数 / 任意）

サイト生成で使う主な変数（未設定でも動作します）:

| 変数 | 既定 | 説明 |
|------|------|------|
| `TRANSLATE_TO_JA` | `1` | `0` にすると日本語への自動翻訳を無効化 |
| `BLOOMBERG_RSS_FEEDS` | 既定フィード | RSS フィードURL（カンマ区切りで上書き） |
| `RATE_KEYWORDS` | 既定キーワード | 金利キーワード（カンマ区切りで上書き） |
| `ANTHROPIC_API_KEY` | 空 | 設定すると要約を Claude で生成（未設定は RSS 概要を使用） |

※ サイトは期間フィルタ用に最大30日・60件ぶんを取得します（`build_site.py` / `site_render.py` の定数で調整可）。

## テスト

```bash
python -m pytest bloomberg_rate_alerts/tests/ -v
```

## 注意

- 表示できるのは Bloomberg の RSS が「その時点で提供している記事」です。RSS は基本的に直近の記事しか
  含まないため、日付指定で大きく過去に遡っても、フィードに無い記事は表示できません。
- 対象国・利上げ/利下げ要因は記事の語句からの**簡易推定**です（参考情報）。
- RSS の提供状況が変わり取得できない場合は `BLOOMBERG_RSS_FEEDS` で別の URL を指定してください。

---

## （任意）メールで送る

Webサイトとは別に、金利ニュースの要約を Gmail で送ることもできます。

```bash
pip install -r requirements.txt
cp .env.example .env            # Gmail の設定を記入
python -m bloomberg_rate_alerts --dry-run   # 送信せず内容を確認
python -m bloomberg_rate_alerts             # 実際に送信
```

- Gmail は**アプリパスワード**が必要です（2段階認証を有効化し
  https://myaccount.google.com/apppasswords で発行 → `.env` の `GMAIL_APP_PASSWORD` に設定）。
- 送信済み記事は記録され、重複送信を防ぎます。
- メール本文をブラウザで確認するプレビューアプリ: `python -m bloomberg_rate_alerts.webapp`
  （`http://127.0.0.1:5000`、`/?demo=1` でサンプル表示）。

メール用の主な `.env` 変数:

| 変数 | 必須 | 説明 |
|------|:---:|------|
| `GMAIL_ADDRESS` | ✓ | 送信元 Gmail アドレス |
| `GMAIL_APP_PASSWORD` | ✓ | Gmail アプリパスワード（16桁） |
| `MAIL_TO` | | 送信先（省略時は自分宛て） |
| `MAIL_FROM` | | 送信元表示名 |
| `MAX_AGE_HOURS` | | 対象記事の新しさ（既定24h、メール用） |
| `MAX_ARTICLES` | | 1通の最大件数（既定10、メール用） |

`.env` と `sent_articles.json` は `.gitignore` 済みです。認証情報は絶対にコミットしないでください。
