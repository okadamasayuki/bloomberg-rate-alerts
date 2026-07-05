"""記事の要約を生成する。

ANTHROPIC_API_KEY が設定されていれば Claude で日本語要約を生成し、
無ければ RSS の概要（summary）をそのまま短くして使う（フォールバック）。
"""

from __future__ import annotations

import re

from .news_fetcher import Article

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _fallback_summary(article: Article, max_chars: int = 200) -> str:
    text = _strip_html(article.summary) or article.title
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def summarize(
    article: Article,
    matched_keywords: list[str],
    api_key: str = "",
    model: str = "claude-sonnet-5",
) -> str:
    """記事を日本語で要約する。"""
    if not api_key:
        return _fallback_summary(article)

    try:
        from anthropic import Anthropic
    except ImportError:
        return _fallback_summary(article)

    body = _strip_html(article.summary)
    prompt = (
        "以下はブルームバーグの金利関連ニュースです。"
        "日本語で2〜3文に要約し、金利・金融政策への含意が分かるようにしてください。"
        "余計な前置きは不要です。\n\n"
        f"見出し: {article.title}\n"
        f"本文: {body}\n"
    )

    try:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        ]
        summary = "".join(parts).strip()
        return summary or _fallback_summary(article)
    except Exception:
        # API 障害時もアラート自体は届けたいのでフォールバックする。
        return _fallback_summary(article)
