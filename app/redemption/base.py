
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RedemptionJob:
    platform: str
    code: str
    streamer: str


@dataclass(frozen=True)
class RedemptionResult:
    status: str
    platform: str
    code: str
    message: str = ""


class RedemptionAdapter(Protocol):
    platform: str

    async def redeem(
        self,
        job: RedemptionJob,
    ) -> RedemptionResult:
        ...

