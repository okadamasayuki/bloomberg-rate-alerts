"""エントリーポイント.

処理の流れ:
  1. Bloomberg の RSS を取得
  2. 金利関連 & 直近のニュースを抽出
  3. 送信済み（重複）を除外
  4. 各記事を要約（Claude 使用は任意）
  5. Gmail でまとめて送信
  6. 送信済みを記録

使い方:
  python -m bloomberg_rate_alerts            # 実際に送信
  python -m bloomberg_rate_alerts --dry-run  # 送信せず内容を表示
"""

from __future__ import annotations

import argparse
import sys

from .config import Config
from .mailer import send_email
from .news_fetcher import Article, find_rate_news
from .render import build_html, build_subject, build_text
from .state import load_sent, save_sent
from .summarizer import summarize


def run(config: Config, dry_run: bool = False) -> int:
    print("Bloomberg のニュースを取得中...")
    matches = find_rate_news(
        feeds=config.feeds,
        keywords=config.keywords,
        max_age_hours=config.max_age_hours,
    )
    print(f"金利関連（直近{config.max_age_hours}h）: {len(matches)} 件")

    if not matches:
        print("金利関連のニュースはありませんでした。メールは送信しません。")
        return 0

    sent = load_sent(config.state_file)
    fresh = [(a, kws) for (a, kws) in matches if a.uid not in sent]
    fresh = fresh[: config.max_articles]

    if not fresh:
        print("新しい金利ニュースはありません（すべて送信済み）。")
        return 0

    print(f"新規 {len(fresh)} 件を要約します...")
    items: list[tuple[Article, list[str], str]] = []
    for article, keywords in fresh:
        summary = summarize(
            article,
            keywords,
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
        )
        items.append((article, keywords, summary))
        print(f"  - {article.title}")

    subject = build_subject(items)
    text_body = build_text(items)
    html_body = build_html(items)

    if dry_run:
        print("\n--- DRY RUN: 送信内容 ---")
        print(f"件名: {subject}\n")
        print(text_body)
        return 0

    config.validate_mail()
    print(f"Gmail 送信中 -> {config.mail_to}")
    send_email(
        gmail_address=config.gmail_address,
        app_password=config.gmail_app_password,
        mail_from=config.mail_from,
        mail_to=config.mail_to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    print("送信完了。")

    for article, _, _ in items:
        sent.add(article.uid)
    save_sent(config.state_file, sent)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bloomberg の金利関連ニュースを Gmail に要約送信する。"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="メールを送信せず、送信予定の内容を表示する。",
    )
    args = parser.parse_args(argv)

    config = Config.from_env()
    try:
        return run(config, dry_run=args.dry_run)
    except Exception as exc:  # 実運用でスタックトレースを出しつつ非0で終了
        print(f"エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
