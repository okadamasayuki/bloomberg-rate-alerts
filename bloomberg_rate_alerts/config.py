"""設定の読み込み.

環境変数（または .env ファイル）から設定値を読み込む。
認証情報はコードに直接書かず、必ず環境変数で渡すこと。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_dotenv() -> None:
    """python-dotenv があれば .env を読み込む（無くても動作する）。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


# Bloomberg の公開 RSS フィード（マーケット/経済系）。
# フィードが利用できない場合は BLOOMBERG_RSS_FEEDS で上書き可能。
DEFAULT_FEEDS = [
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.bloomberg.com/economics/news.rss",
    "https://feeds.bloomberg.com/politics/news.rss",
]

# 金利関連の記事を拾うためのキーワード（大文字小文字は無視）。
DEFAULT_KEYWORDS = [
    # 英語
    "interest rate", "interest rates", "rate hike", "rate cut",
    "rate hikes", "rate cuts", "rate decision", "rate path",
    "fed", "federal reserve", "fomc", "central bank", "monetary policy",
    "yield", "yields", "treasury", "bond yield", "basis point",
    "boj", "ecb", "bank of japan", "hawkish", "dovish", "tightening",
    "easing", "benchmark rate", "policy rate", "inflation target",
    # 日本語
    "金利", "利上げ", "利下げ", "政策金利", "長期金利", "国債利回り",
    "利回り", "日銀", "日本銀行", "連邦準備", "金融政策", "量的緩和",
    "引き締め", "緩和", "中央銀行", "国債", "債券",
]


@dataclass
class Config:
    # ニュース取得
    feeds: list[str] = field(default_factory=lambda: list(DEFAULT_FEEDS))
    keywords: list[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    max_age_hours: int = 24  # この時間以内の記事のみ対象
    max_articles: int = 10   # 1回のメールに含める最大件数

    # 要約 (Anthropic Claude API / 任意)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    # 見出し・要約を日本語に自動翻訳する（APIキー不要の無料翻訳）
    translate_to_ja: bool = True

    # Gmail (SMTP)
    gmail_address: str = ""
    gmail_app_password: str = ""
    mail_to: str = ""
    mail_from: str = ""

    # 状態ファイル（送信済み記事の重複送信を防ぐ）
    state_file: str = "sent_articles.json"

    @classmethod
    def from_env(cls) -> "Config":
        _load_dotenv()

        feeds_env = os.getenv("BLOOMBERG_RSS_FEEDS", "")
        keywords_env = os.getenv("RATE_KEYWORDS", "")

        gmail = os.getenv("GMAIL_ADDRESS", "")
        return cls(
            feeds=_split_csv(feeds_env) or list(DEFAULT_FEEDS),
            keywords=_split_csv(keywords_env) or list(DEFAULT_KEYWORDS),
            max_age_hours=int(os.getenv("MAX_AGE_HOURS", "24")),
            max_articles=int(os.getenv("MAX_ARTICLES", "10")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
            translate_to_ja=os.getenv("TRANSLATE_TO_JA", "1") != "0",
            gmail_address=gmail,
            gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
            mail_to=os.getenv("MAIL_TO", gmail),
            mail_from=os.getenv("MAIL_FROM", gmail),
            state_file=os.getenv("STATE_FILE", "sent_articles.json"),
        )

    def validate_mail(self) -> None:
        missing = [
            name
            for name, value in (
                ("GMAIL_ADDRESS", self.gmail_address),
                ("GMAIL_APP_PASSWORD", self.gmail_app_password),
                ("MAIL_TO", self.mail_to),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Gmail 送信に必要な環境変数が不足しています: "
                + ", ".join(missing)
            )
