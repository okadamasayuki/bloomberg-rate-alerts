"""メール本文（プレーンテキスト / HTML）を組み立てる。"""

from __future__ import annotations

import html
from datetime import datetime

from .news_fetcher import Article


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "日時不明"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def build_subject(items: list[tuple[Article, list[str], str]]) -> str:
    count = len(items)
    lead = items[0][0].title if items else ""
    if len(lead) > 40:
        lead = lead[:40] + "…"
    return f"【金利ニュース {count}件】{lead}"


def build_text(items: list[tuple[Article, list[str], str]]) -> str:
    lines = ["ブルームバーグの金利関連ニュース\n", "=" * 40, ""]
    for i, (article, keywords, summary) in enumerate(items, 1):
        lines.append(f"{i}. {article.title}")
        lines.append(f"   要約: {summary}")
        lines.append(f"   媒体: {article.source} / {_fmt_date(article.published)}")
        lines.append(f"   キーワード: {', '.join(keywords)}")
        lines.append(f"   リンク: {article.link}")
        lines.append("")
    return "\n".join(lines)


def build_html(items: list[tuple[Article, list[str], str]]) -> str:
    cards = []
    for i, (article, keywords, summary) in enumerate(items, 1):
        title = html.escape(article.title)
        link = html.escape(article.link)
        cards.append(
            f"""
            <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin-bottom:16px;">
              <div style="font-size:16px;font-weight:600;margin-bottom:8px;">
                {i}. <a href="{link}" style="color:#0b57d0;text-decoration:none;">{title}</a>
              </div>
              <div style="font-size:14px;color:#333;line-height:1.6;margin-bottom:8px;">
                {html.escape(summary)}
              </div>
              <div style="font-size:12px;color:#777;">
                {html.escape(article.source)} ・ {_fmt_date(article.published)}<br>
                キーワード: {html.escape(', '.join(keywords))}
              </div>
            </div>
            """
        )
    return f"""
    <html><body style="font-family:sans-serif;background:#f6f6f6;padding:24px;">
      <div style="max-width:640px;margin:0 auto;">
        <h2 style="color:#111;">ブルームバーグ 金利関連ニュース</h2>
        <p style="color:#555;font-size:13px;">検出 {len(items)} 件</p>
        {''.join(cards)}
        <p style="color:#999;font-size:11px;">
          このメールは bloomberg_rate_alerts により自動送信されています。
        </p>
      </div>
    </body></html>
    """
