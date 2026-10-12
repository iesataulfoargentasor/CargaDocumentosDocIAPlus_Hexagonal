from dataclasses import dataclass, field
from typing import BinaryIO

@dataclass(frozen=True)
class UploadCommand:
    metadata: dict[str, str]
    stream: BinaryIO | None
    filename: str
    relation: dict[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class DownloadResult:
    content: bytes
    filename: str
    mime: str
