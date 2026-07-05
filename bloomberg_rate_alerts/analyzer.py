"""記事から「対象国」「利上げ要因/利下げ要因」「判断理由」をキーワードで推定する.

APIキー不要のルールベース。記事本文（英語/日本語）に含まれる語句から
・どの国の金融政策に関する話か
・金利を上げる方向の材料か、下げる方向の材料か
・そう判断した根拠（具体的な材料と、それが金利に効く仕組み）
を推定する。あくまで簡易推定であり、断定はしない。
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Analysis:
    country: str      # 例: "米国" / "特定できず"
    direction: str    # "up" | "down" | "neutral"
    label: str        # "利上げ要因" | "利下げ要因" | "中立・判断が難しい"
    reason: str       # 判断理由の文章（詳しめ）


# 対象国の判定（パターン: 英語は語頭境界、日本語は部分一致）
_COUNTRIES: list[tuple[str, list[str]]] = [
    ("米国", ["fed", "federal reserve", "fomc", "powell", "treasury", "treasuries",
              "dollar", "greenback", "frb", "米", "ドル", "連邦準備"]),
    ("日本", ["boj", "bank of japan", "ueda", "yen", "jgb",
              "日銀", "日本銀行", "円"]),
    ("ユーロ圏", ["ecb", "european central bank", "lagarde", "euro", "eurozone",
                  "欧州", "ユーロ"]),
    ("英国", ["boe", "bank of england", "bailey", "sterling", "gilt",
              "britain", "england", "ポンド", "英"]),
    ("中国", ["pboc", "yuan", "renminbi", "chinese", "china", "中国", "人民元"]),
    ("豪州", ["rba", "reserve bank of australia", "aussie", "豪"]),
    ("カナダ", ["boc", "bank of canada", "loonie", "カナダ"]),
    ("ブラジル", ["bcb", "brazil", "brazilian", "durigan", "haddad",
                  "ブラジル", "ドゥリガン", "ハダジ", "レアル"]),
]

# カテゴリごとの「なぜその方向に効くのか」の説明
_EXPLAIN: dict[str, str] = {
    "inflation_up": "物価の上昇圧力は、中央銀行が金融引き締め（利上げ）で抑えにかかる動機になります",
    "economy_strong": "景気や雇用の強さは需要面から物価を押し上げやすく、利上げ方向に働きます",
    "cb_hawkish": "中央銀行のタカ派的な発言・姿勢は、利上げや高金利の長期化観測を強めます",
    "yields_up": "債券利回りの上昇は、市場が利上げや高金利の継続を織り込んでいることを示します",
    "cut_receding": "利下げ観測の後退は、当面は金利が高止まりしやすいことを意味します",
    "inflation_down": "物価の落ち着きは利上げの必要性を弱め、利下げの余地を広げます",
    "economy_weak": "景気や雇用の弱さは、景気を下支えするための利下げ観測を強めます",
    "cb_dovish": "中央銀行のハト派的な発言・姿勢は、利下げ観測を強めます",
    "yields_down": "債券利回りの低下は、市場が利下げを織り込みつつあることを示します",
    "stimulus": "景気刺激策の動きは、金融緩和（利下げ）と方向性が一致します",
}

# 利上げ方向の材料（pattern, ラベル, カテゴリ）
_HAWKISH: list[tuple[str, str, str]] = [
    ("rate hike", "利上げの動き", "cb_hawkish"),
    ("rate increase", "利上げの動き", "cb_hawkish"),
    ("raise rate", "利上げの動き", "cb_hawkish"),
    ("hike", "利上げ観測", "cb_hawkish"),
    ("tighten", "金融引き締め", "cb_hawkish"),
    ("hawkish", "タカ派的な姿勢", "cb_hawkish"),
    ("higher for longer", "高金利の長期化観測", "cb_hawkish"),
    ("sticky inflation", "インフレの高止まり", "inflation_up"),
    ("inflation acceler", "インフレ加速", "inflation_up"),
    ("inflation rose", "インフレ上昇", "inflation_up"),
    ("inflation jump", "インフレ急伸", "inflation_up"),
    ("inflation surg", "インフレ急騰", "inflation_up"),
    ("price pressure", "物価上昇圧力", "inflation_up"),
    ("strong job", "堅調な雇用", "economy_strong"),
    ("robust", "力強い経済指標", "economy_strong"),
    ("wage growth", "賃金の上昇", "economy_strong"),
    ("stronger-than-expected", "予想を上回る強い指標", "economy_strong"),
    ("beat expectation", "予想を上回る指標", "economy_strong"),
    ("overheat", "景気の過熱", "economy_strong"),
    ("yields climb", "利回りの上昇", "yields_up"),
    ("yields rose", "利回りの上昇", "yields_up"),
    ("yields rise", "利回りの上昇", "yields_up"),
    ("yields jump", "利回りの急伸", "yields_up"),
    ("higher yields", "利回りの上昇", "yields_up"),
    # 日本語
    ("利上げ", "利上げの動き", "cb_hawkish"),
    ("引き締め", "金融引き締め", "cb_hawkish"),
    ("タカ派", "タカ派的な姿勢", "cb_hawkish"),
    ("上昇圧力", "物価・金利の上昇圧力", "inflation_up"),
    ("インフレ加速", "インフレ加速", "inflation_up"),
    ("インフレ高止まり", "インフレの高止まり", "inflation_up"),
    ("高止まり", "インフレの高止まり", "inflation_up"),
    ("賃金上昇", "賃金の上昇", "economy_strong"),
    ("賃金の上昇", "賃金の上昇", "economy_strong"),
    ("利回りが上昇", "利回りの上昇", "yields_up"),
    ("利回り上昇", "利回りの上昇", "yields_up"),
    ("観測の後退", "利下げ観測の後退", "cut_receding"),
    ("観測が後退", "利下げ観測の後退", "cut_receding"),
    ("予想を上回る", "予想を上回る強い指標", "economy_strong"),
]

# 利下げ方向の材料
_DOVISH: list[tuple[str, str, str]] = [
    ("rate cut", "利下げの動き", "cb_dovish"),
    ("cut rate", "利下げの動き", "cb_dovish"),
    ("lower rate", "利下げの動き", "cb_dovish"),
    ("easing", "金融緩和", "cb_dovish"),
    ("dovish", "ハト派的な姿勢", "cb_dovish"),
    ("disinflation", "インフレ鈍化", "inflation_down"),
    ("inflation cool", "インフレの鈍化", "inflation_down"),
    ("inflation slow", "インフレの減速", "inflation_down"),
    ("inflation eas", "インフレの緩和", "inflation_down"),
    ("weak job", "弱い雇用", "economy_weak"),
    ("recession", "景気後退", "economy_weak"),
    ("slowdown", "景気の減速", "economy_weak"),
    ("softer", "軟調な指標", "economy_weak"),
    ("downturn", "景気の悪化", "economy_weak"),
    ("unemployment ros", "失業率の上昇", "economy_weak"),
    ("unemployment rise", "失業率の上昇", "economy_weak"),
    ("layoff", "人員削減", "economy_weak"),
    ("weaker-than-expected", "予想を下回る弱い指標", "economy_weak"),
    ("contraction", "経済の縮小", "economy_weak"),
    ("stimulus", "景気刺激策", "stimulus"),
    ("yields fell", "利回りの低下", "yields_down"),
    ("yields drop", "利回りの低下", "yields_down"),
    ("lower yields", "利回りの低下", "yields_down"),
    # 日本語
    ("利下げ", "利下げの動き", "cb_dovish"),
    ("緩和", "金融緩和", "cb_dovish"),
    ("ハト派", "ハト派的な姿勢", "cb_dovish"),
    ("インフレ鈍化", "インフレの鈍化", "inflation_down"),
    ("インフレ減速", "インフレの減速", "inflation_down"),
    ("景気後退", "景気後退", "economy_weak"),
    ("景気減速", "景気の減速", "economy_weak"),
    ("利回りが低下", "利回りの低下", "yields_down"),
    ("利回り低下", "利回りの低下", "yields_down"),
    ("失業率上昇", "失業率の上昇", "economy_weak"),
    ("失業率の上昇", "失業率の上昇", "economy_weak"),
    ("予想を下回る", "予想を下回る弱い指標", "economy_weak"),
]


def _matches(text: str, pattern: str) -> bool:
    """ASCII は語頭境界（別単語への部分一致を防ぐ）、日本語は部分一致。"""
    if pattern.isascii():
        return re.search(r"(?<![a-z])" + re.escape(pattern), text) is not None
    return pattern in text


def _detect_country(text: str) -> str:
    best, best_score = "特定できず", 0
    for name, patterns in _COUNTRIES:
        score = sum(1 for p in patterns if _matches(text, p))
        if score > best_score:
            best, best_score = name, score
    return best


def _collect(text: str, table: list[tuple[str, str, str]]) -> tuple[list[str], list[str]]:
    """マッチした材料ラベルとカテゴリ（それぞれ重複除去）を返す。"""
    labels: list[str] = []
    cats: list[str] = []
    for pattern, label, cat in table:
        if _matches(text, pattern):
            if label not in labels:
                labels.append(label)
            if cat not in cats:
                cats.append(cat)
    return labels, cats


def _mechanism(cats: list[str], limit: int = 2) -> str:
    parts = [_EXPLAIN[c] for c in cats if c in _EXPLAIN]
    return "。".join(parts[:limit])


def _quote(labels: list[str], limit: int = 4) -> str:
    return "・".join(labels[:limit])


def analyze(text: str) -> Analysis:
    lowered = (text or "").lower()
    country = _detect_country(lowered)

    up_labels, up_cats = _collect(lowered, _HAWKISH)
    down_labels, down_cats = _collect(lowered, _DOVISH)

    if len(up_labels) > len(down_labels):
        direction, label = "up", "利上げ要因"
        reason = (
            f"この記事には「{_quote(up_labels)}」といった材料が見られます。"
            f"{_mechanism(up_cats)}。そのため金利を『上げる』方向に働きやすい内容と判断しました。"
        )
        if down_labels:
            reason += (
                f" ただし「{_quote(down_labels, 3)}」のように"
                f"逆方向（利下げ寄り）の材料も一部含まれるため、方向性の強さには幅があります。"
            )
    elif len(down_labels) > len(up_labels):
        direction, label = "down", "利下げ要因"
        reason = (
            f"この記事には「{_quote(down_labels)}」といった材料が見られます。"
            f"{_mechanism(down_cats)}。そのため金利を『下げる』方向に働きやすい内容と判断しました。"
        )
        if up_labels:
            reason += (
                f" ただし「{_quote(up_labels, 3)}」のように"
                f"逆方向（利上げ寄り）の材料も一部含まれるため、方向性の強さには幅があります。"
            )
    else:
        direction, label = "neutral", "中立・判断が難しい"
        if up_labels and down_labels:
            reason = (
                f"利上げ寄りの材料「{_quote(up_labels, 3)}」と"
                f"利下げ寄りの材料「{_quote(down_labels, 3)}」が同程度に含まれています。"
                f"前者は物価・景気の強さから利上げに、後者はその弱さから利下げに働く傾向があり、"
                f"この記事だけではどちらの方向とも判断しづらい内容です。"
            )
        else:
            reason = (
                "金利の方向性を判断できる具体的な材料"
                "（インフレ動向、景気・雇用、中央銀行のスタンス、債券利回りの動きなど）が"
                "記事から明確に読み取れなかったため、中立と判断しました。"
            )

    return Analysis(country=country, direction=direction, label=label, reason=reason)
