"""デモ/プレビュー用のサンプル記事.

ネットワークや feedparser が使えない環境でも Web アプリで
メールの見た目を確認できるようにするためのダミーデータ。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .news_fetcher import Article


def sample_items() -> list[tuple[Article, list[str], str]]:
    now = datetime.now(timezone.utc)
    data = [
        (
            Article(
                title="Fed holds rates steady, signals two cuts later this year",
                link="https://www.bloomberg.com/news/sample-1",
                summary="<p>The Federal Reserve kept its benchmark interest rate "
                "unchanged, but policymakers signaled they expect to cut rates "
                "twice before year-end as inflation cools.</p>",
                source="Bloomberg Markets",
                published=now - timedelta(hours=2),
            ),
            ["fed", "interest rate", "rate cut", "fomc"],
            "FRBは政策金利を据え置いたが、インフレ鈍化を背景に年内2回の利下げを"
            "見込む姿勢を示した。市場は金融緩和期待を強めている。",
        ),
        (
            Article(
                title="日銀、追加利上げを視野に政策金利の据え置きを決定",
                link="https://www.bloomberg.co.jp/news/sample-2",
                summary="日本銀行は金融政策決定会合で政策金利を据え置いた一方、"
                "賃金と物価の動向次第で追加利上げを検討する姿勢を示した。",
                source="Bloomberg",
                published=now - timedelta(hours=5),
            ),
            ["日銀", "利上げ", "政策金利", "金融政策"],
            "日銀は政策金利を据え置いたが、賃金・物価次第で追加利上げを検討する"
            "とした。長期金利の上昇圧力が意識されている。",
        ),
        (
            Article(
                title="Treasury yields climb as traders trim rate-cut bets",
                link="https://www.bloomberg.com/news/sample-3",
                summary="<p>US Treasury yields rose after stronger-than-expected "
                "jobs data led traders to pare back expectations for near-term "
                "rate cuts.</p>",
                source="Bloomberg Markets",
                published=now - timedelta(hours=8),
            ),
            ["treasury", "yield", "rate cut", "yields"],
            "予想を上回る雇用統計を受け、早期利下げ観測が後退し米国債利回りが上昇。"
            "金利上昇が株式市場の重しとなる可能性がある。",
        ),
    ]
    return data
