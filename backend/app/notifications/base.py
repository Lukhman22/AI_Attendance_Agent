from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class NotificationResult:
    success: bool
    provider: str
    error: str | None = None


class NotificationProvider(ABC):
    name: str

    @abstractmethod
    def send(self, message: str, *, recipient: str | None = None) -> NotificationResult:
        raise NotImplementedError
