"""共通の例外."""


class Refused(Exception):
    """入力エラー・拒否。入口が捕まえて終了コード 2 を返す."""
