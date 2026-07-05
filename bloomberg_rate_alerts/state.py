"""送信済み記事の記録（重複送信を防ぐ）。

シンプルに JSON ファイルへ記事の uid を保存する。
"""

from __future__ import annotations

import json
import os


def load_sent(state_file: str) -> set[str]:
    if not os.path.exists(state_file):
        return set()
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("sent", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_sent(state_file: str, sent: set[str], keep: int = 2000) -> None:
    # 無限に増えないよう直近 keep 件だけ保持する。
    ordered = list(sent)[-keep:]
    tmp = state_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"sent": ordered}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, state_file)
