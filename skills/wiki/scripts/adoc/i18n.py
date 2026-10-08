"""言語に依存する文字列の表。表に無い言語は en を使う."""

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "state_missing": "missing",
        "state_unverified": "unverified",
        "state_unresolved": "unresolved",
        "state_changed": "changed",
        "state_fresh": "fresh",
        "status_header": "Wiki: {wiki_dir}  ({catalogue}, {count} pages)  HEAD {head}",
        "status_col_id": "ID",
        "status_col_state": "State",
        "status_col_base": "Base",
        "status_col_reviewed": "Reviewed",
        "status_col_reason": "Reason",
        "reason_more": "{first} and {n} more",
        "reason_unresolved": "commit not found",
        "reason_pending": "{n} pending findings",
        "status_uncommitted": "Uncommitted (in sources): {files}",
        "status_untracked": "Untracked (in sources): {files}",
        "status_next": "Next: {steps}",
        "next_sync": "sync to rewrite {n} pages",
        "next_stamp": "check the {n} unresolved pages, then stamp --pages {ids}",
        "next_commit": "commit the changes in sources first",
        "next_none": "nothing to do",
        "verbose_sources": "sources",
    },
    "ja": {
        "state_missing": "未生成",
        "state_unverified": "未検証",
        "state_unresolved": "解決不能",
        "state_changed": "変更あり",
        "state_fresh": "最新",
        "status_header": "Wiki: {wiki_dir}  ({catalogue}, {count} ページ)  HEAD {head}",
        "status_col_id": "ID",
        "status_col_state": "状態",
        "status_col_base": "基準",
        "status_col_reviewed": "確認日",
        "status_col_reason": "理由",
        "reason_more": "{first} ほか {n} 件",
        "reason_unresolved": "コミットが見つからない",
        "reason_pending": "保留中の指摘 {n} 件",
        "status_uncommitted": "未コミット（sources に該当）: {files}",
        "status_untracked": "未追跡（sources に該当）: {files}",
        "status_next": "次の操作: {steps}",
        "next_sync": "sync で {n} ページを書き直す",
        "next_stamp": "解決不能の {n} ページは内容を確認して stamp --pages {ids}",
        "next_commit": "sources の変更を先にコミットする",
        "next_none": "対応不要",
        "verbose_sources": "sources",
    },
}


def t(lang: str, key: str, **kw) -> str:
    """lang の文字列を返す。表に無い言語は en、表に無いキーは KeyError."""
    table = STRINGS.get(lang, STRINGS["en"])
    text = table[key] if key in table else STRINGS["en"][key]
    return text.format(**kw) if kw else text
