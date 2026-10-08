"""表示幅を考慮したテキスト整形."""

import unicodedata


def width(s: str) -> int:
    """端末上の表示幅（全角は 2）."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def table(rows: list[list[str]]) -> list[str]:
    """列を揃えた行のリスト。最後の列は詰めない."""
    widths = [max(width(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = []
    for r in rows:
        cells = [c + " " * (widths[i] - width(c)) for i, c in enumerate(r[:-1])] + [r[-1]]
        lines.append("  ".join(cells).rstrip())
    return lines
