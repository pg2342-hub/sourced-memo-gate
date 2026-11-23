"""Load the engagement's source library and look up paragraphs by id (e.g. "D2.p1")."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

PATH = Path(__file__).with_name("corpus.yml")


@dataclass(frozen=True)
class Corpus:
    engagement: str
    client: str
    question: str
    documents: tuple[dict, ...]

    @property
    def paragraphs(self) -> dict[str, str]:
        return {f"{d['id']}.{pid}": text for d in self.documents for pid, text in d["paragraphs"].items()}

    def walled_docs(self) -> set[str]:
        """Documents from any other client engagement."""
        return {d["id"] for d in self.documents if d["engagement"] != self.engagement}

    def walled_paragraphs(self) -> dict[str, str]:
        walled = self.walled_docs()
        return {pid: t for pid, t in self.paragraphs.items() if pid.split(".")[0] in walled}

    def render(self) -> str:
        """The library as the agent sees it: every document with its engagement label and paragraph ids."""
        out = []
        for d in self.documents:
            head = f'<document id="{d["id"]}" engagement="{d["engagement"]}" kind="{d["kind"]}">\n{d["title"]}'
            if d.get("confidential"):
                head += f"\nNOTICE: {d['confidential']}"
            body = "\n".join(f"[{d['id']}.{pid}] {text}" for pid, text in d["paragraphs"].items())
            out.append(f"{head}\n{body}\n</document>")
        return "\n\n".join(out)


@lru_cache(maxsize=1)
def load() -> Corpus:
    raw = yaml.safe_load(PATH.read_text())
    return Corpus(raw["engagement"], raw["client"], raw["question"], tuple(raw["documents"]))
