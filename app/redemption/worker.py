from app.redemption.base import (
    RedemptionAdapter,
    RedemptionJob,
)
from app.redemption.queue import RedemptionQueue


class RedemptionWorker:
    """
    Consumes redemption jobs and sends them to
    the appropriate platform adapter.
    """

    def __init__(
        self,
        queue: RedemptionQueue,
        adapters: dict[str, RedemptionAdapter],
    ):
        self.queue = queue
        self.adapters = adapters

    async def run(self) -> None:
        """
        Continuously process redemption jobs.
        """

        print("[REDEMPTION] Worker started.")

        while True:

            job = await self.queue.get()

            try:
                adapter = self.adapters.get(
                    job.platform
                )

                if adapter is None:
                    print(
                        "[REDEMPTION] "
                        f"No adapter for platform: "
                        f"{job.platform}"
                    )
                    continue

                print(
                    "[REDEMPTION] "
                    f"Processing {job.platform} "
                    f"code: {job.code}"
                )

                result = await adapter.redeem(job)

                print(
                    "[REDEMPTION] "
                    f"Result: {result.status}"
                )

                if result.message:
                    print(
                        "[REDEMPTION] "
                        f"Message: {result.message}"
                    )

            except Exception as exc:
                print(
                    "[REDEMPTION] "
                    f"Error processing "
                    f"{job.platform} code "
                    f"{job.code}: {exc}"
                )

            finally:
                self.queue.task_done()