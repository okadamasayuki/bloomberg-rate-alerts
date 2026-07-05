# Bloomberg 金利ニュース → Gmail アラート

ブルームバーグの RSS ニュースを定期的にチェックし、**金利に関係するニュース**があればその要約を Gmail で自分（または指定アドレス）に送るツールです。

## 仕組み

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
