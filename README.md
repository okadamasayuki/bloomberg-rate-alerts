# Bloomberg 金利ニュース要約

ブルームバーグの RSS ニュースを定期的にチェックし、**金利に関係するニュース**があればその要約を表示・通知するツールです。

- 🌐 **Webサイトとして公開**（おすすめ / スマホでURLから閲覧）… 下記「Webサイトとして公開」
- 📧 メールで送信（任意）… 「メールで送る」

---

## Webサイトとして公開（GitHub Pages）

GitHub Actions が定期的にニュースを取得してページを自動生成し、GitHub Pages で公開します。
スマホのブラウザから URL を開くだけで最新の金利ニュース要約が見られます（PC操作・サーバー不要）。

### 有効化の手順（初回だけ）

1. このリポジトリを **Public（公開）** にする
   （Settings → General → 一番下 Danger Zone → "Change repository visibility"）
   ※ 無料プランの GitHub Pages は公開リポジトリが必要です。コードに秘密情報はありません。
2. **Settings → Pages** で Source を **「GitHub Actions」** に設定
   （ワークフロー側でも自動有効化を試みますが、念のため確認してください）
3. **Actions** タブ →「金利ニュースサイトを生成して公開」→ **Run workflow** で初回実行
4. 完了すると `https://okadamasayuki.github.io/bloomberg-rate-alerts/` で公開されます

以降は3時間ごとに自動更新されます（`.github/workflows/site.yml` の cron で調整可能）。
金利ニュースが無いときは「新着なし」の画面が表示されます。

### ローカルで確認

```bash
pip install feedparser python-dotenv
python -m bloomberg_rate_alerts.build_site --demo   # サンプルで site/index.html を生成
# 実データ: python -m bloomberg_rate_alerts.build_site
open site/index.html   # ブラウザで開く
```

---

## メールで送る（任意）

### 仕組み

1. Bloomberg の公開 RSS フィード（markets / economics / politics）を取得
2. 金利関連キーワード（`金利`, `利上げ`, `FOMC`, `Fed`, `rate hike` など）でフィルタ
3. 直近の記事のうち、まだ送っていないものを抽出
4. 各記事を日本語で要約
   - `ANTHROPIC_API_KEY` があれば **Claude** で2〜3文に要約
   - なければ RSS の概要をそのまま短縮（フォールバック）
5. まとめて **Gmail (SMTP)** で送信
6. 送信済み記事を記録して重複送信を防止

## セットアップ

```bash
pip install -r requirements.txt
cp .env.example .env   # 値を編集
```

### Gmail アプリパスワードの発行

1. Google アカウントで**2段階認証を有効化**
2. https://myaccount.google.com/apppasswords でアプリパスワード（16桁）を発行
3. `.env` の `GMAIL_APP_PASSWORD` に設定（通常のログインパスワードは使えません）

## 使い方

```bash
# 送信せず、送信予定の内容を確認（まずはこれで動作確認）
python -m bloomberg_rate_alerts --dry-run

# 実際に Gmail 送信
python -m bloomberg_rate_alerts
```

金利関連ニュースが無ければメールは送信されません。

## Web アプリ（メール内容をブラウザで確認）

送信されるメールの「件名」と「本文(HTML)」をブラウザでプレビューできます。
そのまま送信ボタンから送ることもできます。

```bash
python -m bloomberg_rate_alerts.webapp
# → http://127.0.0.1:5000 を開く
```

- トップ画面: 実際に取得した金利ニュースでメールをプレビュー
- 「サンプル表示」(`/?demo=1`): ネットワークや設定なしで見た目を確認
- 「このメールを送信」: 確認ダイアログのあと Gmail で送信（`.env` の設定が必要）

環境変数 `WEB_HOST` / `WEB_PORT`（既定 `127.0.0.1:5000`）で待受先を変更できます。

## 定期実行（cron 例）

平日の毎時0分に実行する例:

```cron
0 * * * 1-5 cd /path/to/bloomberg-rate-alerts && /usr/bin/python -m bloomberg_rate_alerts >> alerts.log 2>&1
```

## 設定（.env）

| 変数 | 必須 | 説明 |
|------|:---:|------|
| `GMAIL_ADDRESS` | ✓ | 送信元 Gmail アドレス |
| `GMAIL_APP_PASSWORD` | ✓ | Gmail アプリパスワード（16桁） |
| `MAIL_TO` | | 送信先（省略時は自分宛て） |
| `MAIL_FROM` | | 送信元表示名 |
| `ANTHROPIC_API_KEY` | | Claude 要約を使う場合 |
| `ANTHROPIC_MODEL` | | 既定 `claude-sonnet-5` |
| `MAX_AGE_HOURS` | | 対象記事の新しさ（既定24h） |
| `MAX_ARTICLES` | | 1通の最大件数（既定10） |
| `BLOOMBERG_RSS_FEEDS` | | RSS フィード（カンマ区切りで上書き） |
| `RATE_KEYWORDS` | | 金利キーワード（カンマ区切りで上書き） |

## 注意

- Bloomberg の RSS はレイアウト・提供状況が変わることがあります。取得できない場合は `BLOOMBERG_RSS_FEEDS` で別のフィード URL を指定してください。
- `.env` と `sent_articles.json` は `.gitignore` 済みです。認証情報は絶対にコミットしないでください。

## テスト

```bash
python -m pytest bloomberg_rate_alerts/tests/ -v
```
