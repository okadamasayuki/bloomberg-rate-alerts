"""Bloomberg の RSS フィードからニュースを取得し、金利関連の記事を抽出する。"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Article:
    title: str
    link: str
    summary: str
    source: str
    published: datetime | None

    @property
    def uid(self) -> str:
        """重複判定用のID（link が最も安定）。"""
        return self.link or self.title

    def matched_text(self) -> str:
        return f"{self.title}\n{self.summary}".lower()


def _parse_published(entry) -> datetime | None:
    struct = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if not struct:
        return None
    # struct_time (UTC) -> aware datetime
    return datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)


def fetch_articles(feeds: list[str]) -> list[Article]:
    """全フィードから記事を取得する。取得に失敗したフィードはスキップする。"""
    import feedparser  # 遅延import（取得時のみ依存）

    articles: list[Article] = []
    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        source = getattr(parsed.feed, "title", "") or feed_url
        for entry in parsed.entries:
            articles.append(
                Article(
                    title=getattr(entry, "title", "").strip(),
                    link=getattr(entry, "link", "").strip(),
                    summary=getattr(entry, "summary", "").strip(),
                    source=source,
                    published=_parse_published(entry),
                )
            )
    return articles


def is_recent(article: Article, max_age_hours: int) -> bool:
    if article.published is None:
        # 日付が取れない記事は取りこぼしを防ぐため対象に含める。
        return True
    age = datetime.now(timezone.utc) - article.published
    return age.total_seconds() <= max_age_hours * 3600


def _keyword_matches(text: str, keyword: str) -> bool:
    """キーワードが本文にマッチするか判定する。

    英語など ASCII のキーワードは単語境界で判定する
    （例: "fed" は "Fed" にマッチするが "federal" にはマッチしない）。
    日本語は語境界の概念がないため部分一致で判定する。
    """
    kw = keyword.lower()
    if kw.isascii():
        return re.search(rf"\b{re.escape(kw)}\b", text) is not None
    return kw in text


def is_rate_related(article: Article, keywords: list[str]) -> list[str]:
    """マッチしたキーワードのリストを返す（空なら金利関連ではない）。"""
    text = article.matched_text()
    return [kw for kw in keywords if _keyword_matches(text, kw)]


def _normalize_link(link: str) -> str:
    """重複判定用にURLを正規化（クエリ・末尾スラッシュを除去）。"""
    if not link:
        return ""
    from urllib.parse import urlsplit, urlunsplit

    p = urlsplit(link.strip())
    path = p.path.rstrip("/")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, "", "")).lower()


def find_rate_news(
    feeds: list[str],
    keywords: list[str],
    max_age_hours: int,
) -> list[tuple[Article, list[str]]]:
    """金利関連かつ最近の記事を新しい順で返す（重複記事は除去）。"""
    results: list[tuple[Article, list[str]]] = []
    seen_links: set[str] = set()
    seen_titles: set[str] = set()

    for article in fetch_articles(feeds):
        if not is_recent(article, max_age_hours):
            continue
        matched = is_rate_related(article, keywords)
        if not matched:
            continue

        # 複数フィードに載る同一記事を除外（URL または 見出しが一致）
        link_key = _normalize_link(article.link)
        title_key = article.title.strip()
        if (link_key and link_key in seen_links) or (
            title_key and title_key in seen_titles
        ):
            continue
        if link_key:
            seen_links.add(link_key)
        if title_key:
            seen_titles.add(title_key)

        results.append((article, matched))

    results.sort(
        key=lambda item: item[0].published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return results
