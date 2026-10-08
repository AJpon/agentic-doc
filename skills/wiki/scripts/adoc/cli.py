"""サブコマンドの定義の型."""

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """サブコマンドの定義。help は 1 行の説明."""

    help: str
    add_args: Callable[[argparse.ArgumentParser], None]
    run: Callable[[argparse.Namespace], int]
