"""記事から「対象国」「利上げ要因/利下げ要因」「判断理由」をキーワードで推定する.

APIキー不要のルールベース。記事本文（英語/日本語）に含まれる語句から
・どの国の金融政策に関する話か
・金利を上げる方向の材料か、下げる方向の材料か
・そう判断した根拠
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
    reason: str       # 判断理由の文章


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
]

# 利上げ方向の材料（pattern, 日本語の理由ラベル）
_HAWKISH: list[tuple[str, str]] = [
    ("rate hike", "利上げの動き"), ("rate increase", "利上げの動き"),
    ("raise rate", "利上げの動き"), ("hike", "利上げ観測"),
    ("tighten", "金融引き締め"), ("hawkish", "タカ派的な姿勢"),
    ("higher for longer", "高金利の長期化観測"),
    ("sticky inflation", "インフレの高止まり"),
    ("inflation acceler", "インフレ加速"), ("inflation rose", "インフレ上昇"),
    ("inflation jump", "インフレ急伸"), ("inflation surg", "インフレ急騰"),
    ("price pressure", "物価上昇圧力"), ("strong job", "堅調な雇用"),
    ("robust", "力強い経済指標"), ("wage growth", "賃金の上昇"),
    ("stronger-than-expected", "予想を上回る強い指標"),
    ("beat expectation", "予想を上回る指標"), ("overheat", "景気の過熱"),
    ("yields climb", "利回りの上昇"), ("yields rose", "利回りの上昇"),
    ("yields rise", "利回りの上昇"), ("yields jump", "利回りの急伸"),
    ("higher yields", "利回りの上昇"),
    # 日本語
    ("利上げ", "利上げの動き"), ("引き締め", "金融引き締め"),
    ("タカ派", "タカ派的な姿勢"), ("上昇圧力", "物価・金利の上昇圧力"),
    ("インフレ加速", "インフレ加速"), ("インフレ高止まり", "インフレの高止まり"),
    ("高止まり", "インフレの高止まり"), ("賃金上昇", "賃金の上昇"),
    ("賃金の上昇", "賃金の上昇"), ("利回りが上昇", "利回りの上昇"),
    ("利回り上昇", "利回りの上昇"), ("観測の後退", "利下げ観測の後退"),
    ("観測が後退", "利下げ観測の後退"), ("予想を上回る", "予想を上回る強い指標"),
]

# 利下げ方向の材料
_DOVISH: list[tuple[str, str]] = [
    ("rate cut", "利下げの動き"), ("cut rate", "利下げの動き"),
    ("lower rate", "利下げの動き"), ("easing", "金融緩和"),
    ("dovish", "ハト派的な姿勢"), ("disinflation", "インフレ鈍化"),
    ("inflation cool", "インフレの鈍化"), ("inflation slow", "インフレの減速"),
    ("inflation eas", "インフレの緩和"), ("weak job", "弱い雇用"),
    ("recession", "景気後退"), ("slowdown", "景気の減速"),
    ("softer", "軟調な指標"), ("downturn", "景気の悪化"),
    ("unemployment ros", "失業率の上昇"), ("unemployment rise", "失業率の上昇"),
    ("layoff", "人員削減"), ("weaker-than-expected", "予想を下回る弱い指標"),
    ("contraction", "経済の縮小"), ("stimulus", "景気刺激策"),
    ("yields fell", "利回りの低下"), ("yields drop", "利回りの低下"),
    ("lower yields", "利回りの低下"),
    # 日本語
    ("利下げ", "利下げの動き"), ("緩和", "金融緩和"), ("ハト派", "ハト派的な姿勢"),
    ("インフレ鈍化", "インフレの鈍化"), ("インフレ減速", "インフレの減速"),
    ("景気後退", "景気後退"), ("景気減速", "景気の減速"),
    ("利回りが低下", "利回りの低下"), ("利回り低下", "利回りの低下"),
    ("失業率上昇", "失業率の上昇"), ("失業率の上昇", "失業率の上昇"),
    ("予想を下回る", "予想を下回る弱い指標"),
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


def _collect(text: str, table: list[tuple[str, str]]) -> list[str]:
    reasons: list[str] = []
    for pattern, label in table:
        if _matches(text, pattern) and label not in reasons:
            reasons.append(label)
    return reasons


def analyze(text: str) -> Analysis:
    lowered = (text or "").lower()
    country = _detect_country(lowered)

    up = _collect(lowered, _HAWKISH)
    down = _collect(lowered, _DOVISH)

    if len(up) > len(down):
        direction, label = "up", "利上げ要因"
        reason = (
            f"{'・'.join(up[:3])} が読み取れるため、"
            f"金利を『上げる』方向に働きやすい材料と判断しました。"
        )
    elif len(down) > len(up):
        direction, label = "down", "利下げ要因"
        reason = (
            f"{'・'.join(down[:3])} が読み取れるため、"
            f"金利を『下げる』方向に働きやすい材料と判断しました。"
        )
    else:
        direction, label = "neutral", "中立・判断が難しい"
        if up or down:
            reason = (
                "利上げ材料と利下げ材料が拮抗しており、"
                "方向性は一概に言えません。"
            )
        else:
            reason = (
                "金利の方向性を示す明確な語句が見当たらず、"
                "上げ・下げのどちらの要因かは判断できませんでした。"
            )

    return Analysis(country=country, direction=direction, label=label, reason=reason)
