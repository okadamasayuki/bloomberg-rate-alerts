"""メール送信内容をブラウザで確認する Web アプリ (Flask).

できること:
  - Bloomberg の金利関連ニュースを取得し、送信されるメールの
    「件名」と「本文(HTML)」をプレビュー表示
  - デモモード（?demo=1 / サンプルデータ）で見た目を確認
  - ボタンから実際にメールを送信（Gmail 設定が必要）

起動:
  python -m bloomberg_rate_alerts.webapp
  → http://127.0.0.1:5000 を開く
"""

from __future__ import annotations

import os

from flask import Flask, render_template_string, request

from .config import Config
from .news_fetcher import find_rate_news
from .render import build_html, build_subject, build_text
from .sample_data import sample_items
from .state import load_sent, save_sent
from .summarizer import summarize

app = Flask(__name__)


def _build_items(config: Config, demo: bool):
    """(items, error) を返す。items は (Article, keywords, summary) のリスト。"""
    if demo:
        return sample_items(), None
    try:
        matches = find_rate_news(
            feeds=config.feeds,
            keywords=config.keywords,
            max_age_hours=config.max_age_hours,
        )
    except Exception as exc:  # feedparser 未導入 / ネットワーク不通など
        return [], f"ニュースの取得に失敗しました: {exc}"

    matches = matches[: config.max_articles]
    items = [
        (
            article,
            keywords,
            summarize(
                article,
                keywords,
                api_key=config.anthropic_api_key,
                model=config.anthropic_model,
            ),
        )
        for article, keywords in matches
    ]
    return items, None


PAGE = """
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>金利ニュース メールプレビュー</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         background:#f4f5f7; color:#1a1a1a; }
  @media (prefers-color-scheme: dark) {
    body { background:#16181c; color:#e8e8e8; }
    .card, header { background:#22252b !important; border-color:#33373f !important; }
    .muted { color:#9aa0a8 !important; }
    input { background:#16181c; color:#e8e8e8; border-color:#33373f; }
  }
  header { background:#fff; border-bottom:1px solid #e2e4e8; padding:16px 20px; }
  h1 { font-size:18px; margin:0; }
  .wrap { max-width:820px; margin:0 auto; padding:20px; }
  .card { background:#fff; border:1px solid #e2e4e8; border-radius:10px;
          padding:18px; margin-bottom:18px; }
  .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
  .muted { color:#6b7280; font-size:13px; }
  .subject { font-size:16px; font-weight:600; word-break:break-word; }
  .badge { display:inline-block; font-size:12px; padding:2px 8px; border-radius:999px;
           background:#e8f0fe; color:#1a56db; }
  .badge.warn { background:#fef3c7; color:#92661a; }
  .badge.err  { background:#fde2e1; color:#b42318; }
  .btn { display:inline-block; border:none; border-radius:8px; padding:9px 16px;
         font-size:14px; font-weight:600; cursor:pointer; text-decoration:none; }
  .btn.primary { background:#1a56db; color:#fff; }
  .btn.ghost   { background:transparent; color:#1a56db; border:1px solid #1a56db; }
  .btn:disabled { opacity:.5; cursor:not-allowed; }
  iframe.preview { width:100%; height:640px; border:1px solid #e2e4e8; border-radius:8px;
                   background:#fff; }
  .result.ok  { background:#e7f6ec; color:#1a7f37; border:1px solid #b7e4c4; }
  .result.ng  { background:#fde2e1; color:#b42318; border:1px solid #f4b4b0; }
  .result { padding:10px 14px; border-radius:8px; margin-bottom:16px; font-size:14px; }
  form { margin:0; }
</style>
</head>
<body>
<header><div class="wrap" style="padding-top:0;padding-bottom:0;">
  <h1>📧 ブルームバーグ 金利ニュース — メールプレビュー</h1>
</div></header>

<div class="wrap">

  {% if send_result %}
    <div class="result {{ 'ok' if send_ok else 'ng' }}">{{ send_result }}</div>
  {% endif %}

  <div class="card">
    <div class="row" style="justify-content:space-between;">
      <div class="row">
        {% if demo %}<span class="badge warn">デモ表示（サンプルデータ）</span>
        {% else %}<span class="badge">ライブ取得</span>{% endif %}
        <span class="muted">検出 {{ count }} 件</span>
        {% if uses_claude %}<span class="badge">Claude要約</span>
        {% else %}<span class="muted">RSS概要を使用</span>{% endif %}
      </div>
      <div class="row">
        <a class="btn ghost" href="/">再取得</a>
        <a class="btn ghost" href="/?demo=1">サンプル表示</a>
      </div>
    </div>
    {% if error %}
      <p class="muted" style="margin-top:12px;">
        <span class="badge err">取得エラー</span> {{ error }}<br>
        ローカル環境では <code>pip install -r requirements.txt</code> で feedparser を
        入れてください。まずは「サンプル表示」で見た目を確認できます。
      </p>
    {% endif %}
  </div>

  {% if count > 0 %}
    <div class="card">
      <div class="muted">件名</div>
      <div class="subject">{{ subject }}</div>
    </div>

    <div class="card">
      <div class="row" style="justify-content:space-between; margin-bottom:12px;">
        <div class="muted">本文プレビュー（実際に送られるHTML）</div>
        <form action="/send" method="post" onsubmit="return confirm('この内容でメールを送信しますか？');">
          <button class="btn primary" type="submit" {{ 'disabled' if demo }}>
            {% if demo %}送信（サンプルは不可）{% else %}このメールを送信{% endif %}
          </button>
        </form>
      </div>
      <iframe class="preview" srcdoc="{{ html_body|e }}"></iframe>
    </div>
  {% else %}
    <div class="card">
      <p class="muted">
        表示できる金利関連ニュースがありません。
        「サンプル表示」でメールの見た目を確認できます。
      </p>
    </div>
  {% endif %}

  <p class="muted" style="text-align:center;">
    bloomberg_rate_alerts — メール送信内容プレビュー
  </p>
</div>
</body>
</html>
"""


@app.route("/")
def index():
    config = Config.from_env()
    demo = request.args.get("demo") == "1"
    items, error = _build_items(config, demo=demo)

    subject = build_subject(items) if items else ""
    html_body = build_html(items) if items else ""

    return render_template_string(
        PAGE,
        demo=demo,
        error=error,
        count=len(items),
        subject=subject,
        html_body=html_body,
        uses_claude=bool(config.anthropic_api_key) and not demo,
        send_result=request.args.get("sent_msg"),
        send_ok=request.args.get("sent_ok") == "1",
    )


@app.route("/send", methods=["POST"])
def send():
    from flask import redirect
    from urllib.parse import urlencode

    from .mailer import send_email

    config = Config.from_env()
    try:
        config.validate_mail()
        items, error = _build_items(config, demo=False)
        if error:
            raise RuntimeError(error)
        if not items:
            msg, ok = "送信対象の金利ニュースがありませんでした。", "0"
        else:
            send_email(
                gmail_address=config.gmail_address,
                app_password=config.gmail_app_password,
                mail_from=config.mail_from,
                mail_to=config.mail_to,
                subject=build_subject(items),
                text_body=build_text(items),
                html_body=build_html(items),
            )
            sent = load_sent(config.state_file)
            for article, _, _ in items:
                sent.add(article.uid)
            save_sent(config.state_file, sent)
            msg = f"{len(items)} 件のニュースを {config.mail_to} に送信しました。"
            ok = "1"
    except Exception as exc:
        msg, ok = f"送信に失敗しました: {exc}", "0"

    return redirect("/?" + urlencode({"sent_msg": msg, "sent_ok": ok}))


def main() -> None:
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "5000"))
    debug = os.getenv("WEB_DEBUG", "") == "1"
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
