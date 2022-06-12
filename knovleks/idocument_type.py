#!/usr/bin/env python3

import subprocess

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import Mapping, Set


@dataclass
class DocPart:
    doccontent: str
    elem_idx: int = 0


@dataclass  # type: ignore[misc]
class IdocumentType(ABC):
    href: str
    title: str = ""
    doc_type: str = ""
    tags: Set[str] = field(default_factory=lambda: set())
    metadata: Mapping[str, str] = field(default_factory=lambda: {})
    parts: Sequence[DocPart] = field(default_factory=lambda: [])

    def __post_init__(self):
        self.parse()

    @abstractmethod
    def parse(self):
        raise NotImplementedError

    @staticmethod
    def open_doc(href, elem_idx):
        subprocess.Popen(["/usr/bin/xdg-open", f"{href}"], kstdin=None,
                         stdout=None, stderr=None, close_fds=True)
