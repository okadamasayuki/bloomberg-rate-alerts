"""Bloomberg の RSS フィードからニュースを取得し、金利関連の記事を抽出する。"""

from __future__ import annotations

import calendar
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


def is_rate_related(article: Article, keywords: list[str]) -> list[str]:
    """マッチしたキーワードのリストを返す（空なら金利関連ではない）。"""
    text = article.matched_text()
    return [kw for kw in keywords if kw.lower() in text]


def find_rate_news(
    feeds: list[str],
    keywords: list[str],
    max_age_hours: int,
) -> list[tuple[Article, list[str]]]:
    """金利関連かつ最近の記事を新しい順で返す。"""
    results: list[tuple[Article, list[str]]] = []
    for article in fetch_articles(feeds):
        if not is_recent(article, max_age_hours):
            continue
        matched = is_rate_related(article, keywords)
        if matched:
            results.append((article, matched))

    results.sort(
        key=lambda item: item[0].published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return results
