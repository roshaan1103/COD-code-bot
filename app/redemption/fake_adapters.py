from app.redemption.base import (
    RedemptionJob,
    RedemptionResult,
)


class FakeSteamAdapter:
    platform = "steam"

    async def redeem(
        self,
        job: RedemptionJob,
    ) -> RedemptionResult:
        print()
        print("[FAKE STEAM]")
        print("Received code: [REDACTED]")
        print(f"Streamer: {job.streamer}")
        print("[FAKE STEAM] Redemption simulated.")
        print()

        return RedemptionResult(
            status="SIMULATED",
            platform=job.platform,
            code=job.code,
            message="Steam redemption was simulated.",
        )


class FakeBattleNetAdapter:
    platform = "battle.net"

    async def redeem(
        self,
        job: RedemptionJob,
    ) -> RedemptionResult:
        print()
        print("[FAKE BATTLE.NET]")
        print("Received code: [REDACTED]")
        print(f"Streamer: {job.streamer}")
        print("[FAKE BATTLE.NET] Redemption simulated.")
        print()

        return RedemptionResult(
            status="SIMULATED",
            platform=job.platform,
            code=job.code,
            message="Battle.net redemption was simulated.",
        )