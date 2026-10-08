"""言語に依存する文字列の表。表に無い言語は en を使う."""

STRINGS: dict[str, dict[str, str]] = {
    "en": {},
    "ja": {},
}


def t(lang: str, key: str, **kw) -> str:
    """lang の文字列を返す。表に無いキーは KeyError."""
    table = STRINGS.get(lang, STRINGS["en"])
    text = table[key] if key in table else STRINGS["en"][key]
    return text.format(**kw) if kw else text
