"""静的サイト（GitHub Pages 等）用の HTML ページを生成する.

メールとは別に、スマホでも読みやすいレスポンシブな1ページを出力する。
金利ニュースがあれば要約カードを、無ければ「現在なし」の状態を表示する。
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone

from .news_fetcher import Article

JST = timezone(timedelta(hours=9), "JST")


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return "日時不明"
    return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M")


def _chips(keywords: list[str]) -> str:
    return "".join(
        f'<span class="chip">{html.escape(kw)}</span>' for kw in keywords
    )


def _card(index: int, article: Article, keywords: list[str], summary: str) -> str:
    title = html.escape(article.title)
    link = html.escape(article.link)
    return f"""
      <article class="card">
        <div class="card-top">
          <span class="src">{html.escape(article.source)}</span>
          <time>{_fmt(article.published)}</time>
        </div>
        <h2 class="title">{title}</h2>
        <p class="summary">{html.escape(summary)}</p>
        <div class="chips">{_chips(keywords)}</div>
        <a class="read" href="{link}" target="_blank" rel="noopener">
          記事を読む <span aria-hidden="true">↗</span>
        </a>
      </article>"""


def render_page(
    items: list[tuple[Article, list[str], str]],
    updated_at: datetime,
) -> str:
    count = len(items)
    updated = _fmt(updated_at)

    if count:
        body = "\n".join(
            _card(i, a, kw, s) for i, (a, kw, s) in enumerate(items, 1)
        )
        status = f'<span class="badge on">{count} 件の金利ニュース</span>'
    else:
        body = """
      <div class="empty">
        <div class="empty-mark">🟢</div>
        <p class="empty-title">現在、金利関連の新しいニュースはありません</p>
        <p class="empty-sub">新しいニュースが見つかると、ここに要約が表示されます。</p>
      </div>"""
        status = '<span class="badge off">新着なし</span>'

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>金利ニュース要約</title>
<style>
  :root{{
    --ground:#eef1f5; --card:#ffffff; --ink:#14171c; --muted:#5c6470;
    --line:#e3e6ec; --accent:#1d4ed8; --accent-soft:#e7edfb;
    --chip:#eef1f6; --chip-ink:#42506a; --good:#1a7f43; --good-soft:#e4f4ea;
    --shadow:0 1px 2px rgba(20,25,40,.05), 0 6px 22px rgba(20,25,40,.07);
  }}
  @media (prefers-color-scheme: dark){{
    :root{{
      --ground:#0e1014; --card:#181b21; --ink:#e7eaee; --muted:#98a1b0;
      --line:#282c35; --accent:#7aa2ff; --accent-soft:#18213a;
      --chip:#20242c; --chip-ink:#aab3c2; --good:#4cc27e; --good-soft:#132a1e;
      --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 26px rgba(0,0,0,.45);
    }}
  }}
  *{{box-sizing:border-box;}}
  html,body{{margin:0;}}
  body{{
    font-family:system-ui,-apple-system,"Segoe UI","Hiragino Kaku Gothic ProN",
      "Noto Sans JP",Meiryo,sans-serif;
    background:var(--ground); color:var(--ink); line-height:1.65;
    -webkit-font-smoothing:antialiased; padding:22px 15px 60px;
  }}
  .wrap{{max-width:680px; margin:0 auto;}}

  header{{margin-bottom:18px;}}
  .brand{{display:flex; align-items:center; gap:11px;}}
  .logo{{
    width:40px;height:40px;border-radius:11px;flex:none;
    background:var(--accent-soft); color:var(--accent);
    display:flex;align-items:center;justify-content:center;font-size:21px;
  }}
  h1{{font-size:19px; margin:0; letter-spacing:.2px;}}
  .tagline{{color:var(--muted); font-size:13px; margin:2px 0 0;}}

  .statusbar{{
    display:flex; align-items:center; justify-content:space-between;
    gap:10px; flex-wrap:wrap; margin:16px 0 20px;
  }}
  .badge{{font-size:12.5px; font-weight:650; padding:5px 12px; border-radius:999px;}}
  .badge.on{{background:var(--accent-soft); color:var(--accent);}}
  .badge.off{{background:var(--good-soft); color:var(--good);}}
  .updated{{color:var(--muted); font-size:12.5px; font-variant-numeric:tabular-nums;}}

  .feed{{display:grid; gap:14px;}}
  .card{{
    background:var(--card); border:1px solid var(--line); border-radius:15px;
    padding:17px 17px 15px; box-shadow:var(--shadow);
  }}
  .card-top{{
    display:flex; align-items:center; justify-content:space-between;
    gap:10px; font-size:12px; color:var(--muted); margin-bottom:8px;
  }}
  .src{{font-weight:600; letter-spacing:.02em;}}
  .card-top time{{font-variant-numeric:tabular-nums;}}
  .title{{font-size:16.5px; font-weight:680; line-height:1.5; margin:0 0 8px; text-wrap:balance;}}
  .summary{{font-size:14.5px; color:var(--ink); margin:0 0 12px;}}
  .chips{{display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;}}
  .chip{{
    font-size:11.5px; background:var(--chip); color:var(--chip-ink);
    padding:3px 9px; border-radius:999px;
  }}
  .read{{
    display:inline-flex; align-items:center; gap:5px;
    font-size:13.5px; font-weight:650; color:var(--accent); text-decoration:none;
  }}
  .read:hover{{text-decoration:underline;}}

  .empty{{
    background:var(--card); border:1px solid var(--line); border-radius:16px;
    box-shadow:var(--shadow); padding:44px 22px; text-align:center;
  }}
  .empty-mark{{font-size:34px; margin-bottom:10px;}}
  .empty-title{{font-size:16px; font-weight:650; margin:0 0 6px;}}
  .empty-sub{{color:var(--muted); font-size:13.5px; margin:0;}}

  footer{{margin-top:26px; text-align:center; color:var(--muted); font-size:12px;}}
  footer a{{color:var(--accent); text-decoration:none;}}

  @media (max-width:420px){{
    h1{{font-size:18px;}}
    .title{{font-size:16px;}}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand">
        <div class="logo">📈</div>
        <div>
          <h1>金利ニュース要約</h1>
          <p class="tagline">ブルームバーグの金利関連ニュースを自動でまとめて表示</p>
        </div>
      </div>
    </header>

    <div class="statusbar">
      {status}
      <span class="updated">最終更新: {updated}</span>
    </div>

    <main class="feed">
{body}
    </main>

    <footer>
      ブルームバーグのRSSを定期チェックして自動生成しています。<br>
      直近24時間以内・金利関連のニュースのみを表示します。
    </footer>
  </div>
</body>
</html>
"""
