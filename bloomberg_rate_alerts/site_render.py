"""静的サイト（GitHub Pages 等）用の HTML ページを生成する.

メールとは別に、スマホでも読みやすいレスポンシブな1ページを出力する。
金利ニュースがあれば要約カードを、無ければ「現在なし」の状態を表示する。
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone

from .news_fetcher import Article

JST = timezone(timedelta(hours=9), "JST")

# クイック期間プリセット（ラベル, 時間）。0 は「すべて」。
PERIODS: list[tuple[str, int]] = [
    ("24時間", 24), ("3日", 72), ("7日", 168), ("すべて", 0)
]
DEFAULT_HOURS = 24  # 初期表示
# サイトが取得しておく範囲（RSSが持つ範囲まで／最大30日）
FETCH_HOURS = 24 * 30


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return "日時不明"
    return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M")


def _chips(keywords: list[str]) -> str:
    return "".join(
        f'<span class="chip">{html.escape(kw)}</span>' for kw in keywords
    )


def _analysis_block(analysis) -> str:
    if analysis is None:
        return ""
    dir_label = {"up": "▲ 利上げ要因", "down": "▼ 利下げ要因", "neutral": "＝ 中立"}
    tag = dir_label.get(analysis.direction, analysis.label)
    return f"""
        <div class="analysis {analysis.direction}">
          <div class="analysis-head">
            <span class="dir">{html.escape(tag)}</span>
            <span class="country">対象: {html.escape(analysis.country)}</span>
          </div>
          <p class="reason">{html.escape(analysis.reason)}</p>
        </div>"""


def _card(
    index: int,
    article: Article,
    keywords: list[str],
    summary: str,
    analysis=None,
    hidden: bool = False,
) -> str:
    title = html.escape(article.title)
    link = html.escape(article.link)
    epoch = "" if article.published is None else str(int(article.published.timestamp()))
    style = ' style="display:none"' if hidden else ""
    return f"""
      <article class="card" data-epoch="{epoch}"{style}>
        <div class="card-top">
          <span class="src">{html.escape(article.source)}</span>
          <time>{_fmt(article.published)}</time>
        </div>
        <h2 class="title">{title}</h2>
        <p class="summary">{html.escape(summary)}</p>
        {_analysis_block(analysis)}
        <div class="chips">{_chips(keywords)}</div>
        <a class="read" href="{link}" target="_blank" rel="noopener">
          記事を読む <span aria-hidden="true">↗</span>
        </a>
      </article>"""


def render_page(
    items: list,
    updated_at: datetime,
) -> str:
    count = len(items)
    updated = _fmt(updated_at)

    # 既定期間(24時間)より古いカードは初期状態で隠す（JS無効でも既定表示）
    def _is_hidden(item) -> bool:
        published = item[0].published
        if published is None:
            return False
        age_h = (updated_at - published).total_seconds() / 3600
        return age_h > DEFAULT_HOURS

    visible_now = sum(1 for item in items if not _is_hidden(item))

    period_buttons = "".join(
        f'<button class="period-btn{" active" if hours == DEFAULT_HOURS else ""}" '
        f'data-hours="{hours}">{html.escape(label)}</button>'
        for label, hours in PERIODS
    )

    # 日付レンジ入力の下限/上限（取得済みデータの範囲）
    dates = [item[0].published for item in items if item[0].published]
    if dates:
        dmin = min(dates).astimezone(JST).strftime("%Y-%m-%d")
        dmax = max(dates).astimezone(JST).strftime("%Y-%m-%d")
    else:
        dmin = dmax = updated_at.astimezone(JST).strftime("%Y-%m-%d")
    date_attrs = f'min="{dmin}" max="{dmax}"'

    period_bar = f"""<div class="filters">
      <div class="periods">
        <span class="periods-label">期間</span>{period_buttons}
      </div>
      <div class="daterange">
        <span class="periods-label">日付指定</span>
        <input type="date" id="date-from" {date_attrs} aria-label="最初の日">
        <span class="tilde">〜</span>
        <input type="date" id="date-to" {date_attrs} aria-label="最後の日">
        <button class="period-btn" id="date-clear">クリア</button>
      </div>
    </div>"""

    if count:
        body = "\n".join(
            _card(
                i,
                item[0],
                item[1],
                item[2],
                item[3] if len(item) > 3 else None,
                hidden=_is_hidden(item),
            )
            for i, item in enumerate(items, 1)
        )
        # 選択期間に該当が無いとき用（JSで表示制御）
        pe_style = "" if visible_now == 0 else ' style="display:none"'
        body += f"""
      <div class="empty" id="period-empty"{pe_style}>
        <div class="empty-mark">🔍</div>
        <p class="empty-title">この期間に金利ニュースはありません</p>
        <p class="empty-sub">上の「期間」を長くすると表示されることがあります。</p>
      </div>"""
        status = (
            '<span class="badge on"><span id="visible-count">'
            f'{visible_now}</span> 件の金利ニュース</span>'
        )
    else:
        body = """
      <div class="empty">
        <div class="empty-mark">🟢</div>
        <p class="empty-title">現在、金利関連の新しいニュースはありません</p>
        <p class="empty-sub">新しいニュースが見つかると、ここに要約が表示されます。</p>
      </div>"""
        status = '<span class="badge off">新着なし</span>'
        period_bar = ""

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
    --up:#c2410c; --up-soft:#fdecdf; --down:#0f766e; --down-soft:#dcf1ee;
    --neutral:#5c6470; --neutral-soft:#eceef2;
    --shadow:0 1px 2px rgba(20,25,40,.05), 0 6px 22px rgba(20,25,40,.07);
  }}
  @media (prefers-color-scheme: dark){{
    :root{{
      --ground:#0e1014; --card:#181b21; --ink:#e7eaee; --muted:#98a1b0;
      --line:#282c35; --accent:#7aa2ff; --accent-soft:#18213a;
      --chip:#20242c; --chip-ink:#aab3c2; --good:#4cc27e; --good-soft:#132a1e;
      --up:#f4a06a; --up-soft:#2b1c12; --down:#5cc9bd; --down-soft:#0f2521;
      --neutral:#98a1b0; --neutral-soft:#20242c;
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

  .filters{{
    margin:16px 0 4px; padding:12px 13px; border-radius:12px;
    background:var(--card); border:1px solid var(--line); box-shadow:var(--shadow);
    display:grid; gap:10px;
  }}
  .periods{{display:flex; align-items:center; gap:7px; flex-wrap:wrap;}}
  .periods-label{{font-size:12px; color:var(--muted); margin-right:2px; min-width:60px;}}
  .daterange{{display:flex; align-items:center; gap:7px; flex-wrap:wrap;}}
  .daterange input[type="date"]{{
    font:inherit; font-size:13px; color:var(--ink);
    background:var(--ground); border:1px solid var(--line);
    border-radius:9px; padding:6px 9px; -webkit-appearance:none; appearance:none;
    min-width:0; flex:1 1 130px;
  }}
  .daterange input[type="date"]:focus{{outline:none; border-color:var(--accent);}}
  .daterange .tilde{{color:var(--muted); flex:none;}}
  .period-btn{{
    font:inherit; font-size:13px; font-weight:600; cursor:pointer;
    padding:6px 14px; border-radius:999px;
    border:1px solid var(--line); background:var(--card); color:var(--ink);
    -webkit-appearance:none; appearance:none;
  }}
  .period-btn:hover{{border-color:var(--accent);}}
  .period-btn.active{{background:var(--accent); border-color:var(--accent); color:#fff;}}
  .period-btn:focus-visible{{outline:2px solid var(--accent); outline-offset:2px;}}

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

  .analysis{{
    border-radius:11px; padding:11px 13px; margin:0 0 12px;
    border:1px solid var(--line); background:var(--neutral-soft);
  }}
  .analysis.up{{background:var(--up-soft); border-color:color-mix(in srgb,var(--up) 30%,transparent);}}
  .analysis.down{{background:var(--down-soft); border-color:color-mix(in srgb,var(--down) 30%,transparent);}}
  .analysis-head{{display:flex; align-items:center; gap:9px; flex-wrap:wrap; margin-bottom:5px;}}
  .analysis .dir{{font-size:13px; font-weight:750;}}
  .analysis.up .dir{{color:var(--up);}}
  .analysis.down .dir{{color:var(--down);}}
  .analysis.neutral .dir{{color:var(--neutral);}}
  .analysis .country{{
    font-size:11.5px; font-weight:600; color:var(--ink);
    background:var(--card); border:1px solid var(--line);
    padding:2px 9px; border-radius:999px;
  }}
  .analysis .reason{{font-size:12.5px; color:var(--ink); margin:0; line-height:1.6;}}

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

    {period_bar}

    <div class="statusbar">
      {status}
      <span class="updated">最終更新: {updated}</span>
    </div>

    <main class="feed">
{body}
    </main>

    <footer>
      ブルームバーグのRSSを定期チェックして自動生成しています。<br>
      金利関連のニュースのみを表示します（期間は上部で切り替え）。<br>
      英語記事の見出し・要約は日本語に自動翻訳しています。<br>
      対象国・利上げ/利下げ要因は記事の語句からの簡易推定です（参考情報）。
    </footer>
  </div>

  <script>
  (function() {{
    var presets = document.querySelectorAll('.period-btn[data-hours]');
    var cards = document.querySelectorAll('.card[data-epoch]');
    var countEl = document.getElementById('visible-count');
    var emptyEl = document.getElementById('period-empty');
    var fromEl = document.getElementById('date-from');
    var toEl = document.getElementById('date-to');
    var clearEl = document.getElementById('date-clear');

    function setVisible(show) {{
      var visible = 0;
      cards.forEach(function(c, i) {{
        c.style.display = show[i] ? '' : 'none';
        if (show[i]) visible++;
      }});
      if (countEl) countEl.textContent = visible;
      if (emptyEl) emptyEl.style.display = (visible === 0 && cards.length > 0) ? '' : 'none';
    }}

    function applyPreset(hours) {{
      var now = Date.now() / 1000;
      var show = [];
      cards.forEach(function(c) {{
        var ep = c.getAttribute('data-epoch');
        show.push(!ep ? true : (hours === 0 || (now - parseFloat(ep)) / 3600 <= hours));
      }});
      setVisible(show);
    }}

    function jstMs(str, endOfDay) {{
      return Date.parse(str + (endOfDay ? 'T23:59:59+09:00' : 'T00:00:00+09:00'));
    }}

    function applyRange() {{
      var f = fromEl && fromEl.value, t = toEl && toEl.value;
      if (!f && !t) return false;
      presets.forEach(function(x) {{ x.classList.remove('active'); }});
      var lo = f ? jstMs(f, false) : -Infinity;
      var hi = t ? jstMs(t, true) : Infinity;
      var show = [];
      cards.forEach(function(c) {{
        var ep = c.getAttribute('data-epoch');
        if (!ep) {{ show.push(false); return; }}
        var ms = parseFloat(ep) * 1000;
        show.push(ms >= lo && ms <= hi);
      }});
      setVisible(show);
      return true;
    }}

    presets.forEach(function(b) {{
      b.addEventListener('click', function() {{
        presets.forEach(function(x) {{ x.classList.remove('active'); }});
        b.classList.add('active');
        if (fromEl) fromEl.value = '';
        if (toEl) toEl.value = '';
        applyPreset(parseInt(b.getAttribute('data-hours'), 10));
      }});
    }});
    if (fromEl) fromEl.addEventListener('change', applyRange);
    if (toEl) toEl.addEventListener('change', applyRange);
    if (clearEl) clearEl.addEventListener('click', function() {{
      if (fromEl) fromEl.value = '';
      if (toEl) toEl.value = '';
      var def = document.querySelector('.period-btn[data-hours="{DEFAULT_HOURS}"]');
      if (def) def.click();
    }});

    var active = document.querySelector('.period-btn.active');
    if (active) applyPreset(parseInt(active.getAttribute('data-hours'), 10));
  }})();
  </script>
</body>
</html>
"""
