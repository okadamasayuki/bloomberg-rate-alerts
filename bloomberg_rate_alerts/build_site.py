"""静的サイトを生成する（GitHub Actions などで定期実行する想定）.

Bloomberg の金利関連ニュースを取得し、要約付きの1ページを
`site/index.html` として書き出す。金利ニュースが無ければ
「現在なし」の状態のページを出力する。

使い方:
  python -m bloomberg_rate_alerts.build_site            # ライブ取得
  python -m bloomberg_rate_alerts.build_site --demo     # サンプルで生成（動作確認用）
  python -m bloomberg_rate_alerts.build_site --out dir  # 出力先を指定
"""

from __future__ import annotations

import argparse
import os
from dataclasses import replace
from datetime import datetime, timezone

from .config import Config
from .news_fetcher import find_rate_news
from .sample_data import sample_items
from .site_render import render_page
from .summarizer import summarize
from .translate import to_japanese


def build_items(config: Config, demo: bool):
    if demo:
        return sample_items()

    matches = find_rate_news(
        feeds=config.feeds,
        keywords=config.keywords,
        max_age_hours=config.max_age_hours,
    )
    matches = matches[: config.max_articles]

    items = []
    for article, keywords in matches:
        summary = summarize(
            article,
            keywords,
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
        )
        if config.translate_to_ja:
            # 見出しと要約を日本語化（すでに日本語なら素通し・失敗時は原文）
            article = replace(article, title=to_japanese(article.title))
            summary = to_japanese(summary)
        items.append((article, keywords, summary))
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="金利ニュースの静的サイトを生成する。")
    parser.add_argument("--demo", action="store_true", help="サンプルデータで生成する。")
    parser.add_argument("--out", default="site", help="出力ディレクトリ（既定: site）。")
    args = parser.parse_args(argv)

    config = Config.from_env()

    if args.demo:
        items = build_items(config, demo=True)
    else:
        try:
            items = build_items(config, demo=False)
        except Exception as exc:
            # 取得に失敗してもサイト自体は空状態で更新する（前回分を壊さない）
            print(f"ニュース取得に失敗しました（空ページを生成）: {exc}")
            items = []

    html = render_page(items, updated_at=datetime.now(timezone.utc))

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    head = items[0][0].title if items else "-"
    print(f"生成しました: {out_path}（金利ニュース {len(items)} 件）先頭見出し: {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
