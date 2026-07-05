"""ニュース抽出・要約フォールバックのテスト（ネットワーク不要）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bloomberg_rate_alerts.config import DEFAULT_KEYWORDS
from bloomberg_rate_alerts.news_fetcher import (
    Article,
    is_rate_related,
    is_recent,
)
from bloomberg_rate_alerts.render import build_subject, build_text
from bloomberg_rate_alerts.summarizer import summarize


def _article(title: str, summary: str = "", published=None) -> Article:
    return Article(
        title=title,
        link="https://example.com/a",
        summary=summary,
        source="Bloomberg",
        published=published,
    )


def test_rate_related_english():
    art = _article("Fed signals another rate hike amid inflation")
    assert is_rate_related(art, DEFAULT_KEYWORDS)


def test_rate_related_japanese():
    art = _article("日銀が金利政策を据え置き", "政策金利を維持")
    matched = is_rate_related(art, DEFAULT_KEYWORDS)
    assert "金利" in matched


def test_not_rate_related():
    art = _article("Apple unveils new iPhone lineup")
    assert not is_rate_related(art, DEFAULT_KEYWORDS)


def test_fed_substring_not_matched():
    # "federal" の一部として "fed" に部分一致してはいけない（金利無関係）
    art = _article("Trump escalates fight over federal pipeline rules")
    assert not is_rate_related(art, DEFAULT_KEYWORDS)


def test_fed_word_is_matched():
    art = _article("The Fed is expected to hold policy this week")
    assert "fed" in is_rate_related(art, DEFAULT_KEYWORDS)


def test_is_recent_true():
    recent = datetime.now(timezone.utc) - timedelta(hours=2)
    assert is_recent(_article("x", published=recent), max_age_hours=24)


def test_is_recent_false():
    old = datetime.now(timezone.utc) - timedelta(hours=48)
    assert not is_recent(_article("x", published=old), max_age_hours=24)


def test_is_recent_none_included():
    # 日付不明は取りこぼし防止で対象に含める
    assert is_recent(_article("x", published=None), max_age_hours=24)


def test_summarize_fallback_no_key():
    art = _article("Fed rate decision", summary="<p>The Fed raised rates.</p>")
    out = summarize(art, ["fed"], api_key="")
    assert "Fed raised rates" in out
    assert "<p>" not in out  # HTMLタグは除去される


def test_render_subject_and_body():
    art = _article("Fed hikes rates", summary="text", published=None)
    items = [(art, ["fed"], "要約テキスト")]
    assert "金利ニュース 1件" in build_subject(items)
    body = build_text(items)
    assert "Fed hikes rates" in body
    assert "要約テキスト" in body
