"""日付引数の扱い."""

import argparse
import datetime
import re


def iso_date(value: str) -> str:
    """argparse の type。YYYY-MM-DD だけを受け付ける."""
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value}")


def today() -> str:
    """ローカルタイムゾーンでの今日の日付."""
    return datetime.datetime.now().astimezone().date().isoformat()
