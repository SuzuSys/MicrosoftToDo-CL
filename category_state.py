# category_state.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_START = 1


@dataclass
class CategoryState:
    current_index: int = DEFAULT_START

    @property
    def current_name(self) -> str:
        return f"c{self.current_index}"

    def advance(self) -> None:
        self.current_index += 1


def load_state(path: Path) -> CategoryState:
    if not path.exists():
        return CategoryState()

    data = json.loads(path.read_text(encoding="utf-8"))
    return CategoryState(
        current_index=int(data.get("current_index", DEFAULT_START)),
    )


def save_state(path: Path, state: CategoryState) -> None:
    path.write_text(
        json.dumps(
            {
                "current_index": state.current_index,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
