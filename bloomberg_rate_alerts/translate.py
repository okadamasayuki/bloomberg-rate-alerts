"""テキストを日本語に翻訳する（APIキー不要）.

Google の無料翻訳エンドポイントを利用する。失敗した場合は元のテキストを
そのまま返すので、翻訳できなくてもサイト自体は壊れない（英語のまま表示）。
すでに日本語のテキストは翻訳しない（無駄な通信を避ける）。
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

# ひらがな・カタカナ・CJK漢字のいずれかを含めば「日本語」とみなす
_JA_RE = re.compile(r"[぀-ヿ㐀-鿿ｦ-ﾟ]")
_ENDPOINT = "https://translate.googleapis.com/translate_a/single"


def is_japanese(text: str) -> bool:
    return bool(_JA_RE.search(text or ""))


def to_japanese(text: str, timeout: float = 10.0) -> str:
    """text を日本語に翻訳する。失敗時・不要時は元テキストを返す。"""
    text = (text or "").strip()
    if not text or is_japanese(text):
        return text

    params = urllib.parse.urlencode(
        {"client": "gtx", "sl": "auto", "tl": "ja", "dt": "t", "q": text}
    )
    url = f"{_ENDPOINT}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # data[0] は [翻訳片, 原文片, ...] の配列
        chunks = data[0] or []
        out = "".join(c[0] for c in chunks if c and c[0])
        return out.strip() or text
    except Exception:
        return text
