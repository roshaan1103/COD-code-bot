import asyncio

from app.redemption.base import (
    RedemptionAdapter,
    RedemptionJob,
)
from app.redemption.queue import RedemptionQueue


class RedemptionWorker:
    """
    Consumes redemption jobs and sends them to
    the appropriate platform adapter.

    A RATE_LIMITED result pauses processing without
    removing subsequent jobs from the queue.
    """

    def __init__(
        self,
        queue: RedemptionQueue,
        adapters: dict[str, RedemptionAdapter],
    ):
        self.queue = queue
        self.adapters = adapters

        # The worker can process jobs immediately at startup.
        self._resume_event = asyncio.Event()
        self._resume_event.set()

    def resume(self) -> None:
        """
        Explicitly resume redemption processing.

        Call this only after investigating the rate limit
        and deciding it is safe to continue.
        """
        if not self._resume_event.is_set():
            self._resume_event.set()
            print("[REDEMPTION] Processing resumed.")

    async def run(self) -> None:
        """
        Process jobs continuously.

        When rate-limited, wait before retrieving another job.
        This preserves queued jobs while the worker is paused.
        """

        print("[REDEMPTION] Worker started.")

        while True:
            # Wait BEFORE dequeuing anything.
            # Jobs remain queued while processing is paused.
            await self._resume_event.wait()

            job = await self.queue.get()

            try:
                adapter = self.adapters.get(job.platform)

                if adapter is None:
                    print(
                        "[REDEMPTION] "
                        f"No adapter for platform: {job.platform}"
                    )
                    continue

                # Do not print the actual redemption code here.
                print(
                    "[REDEMPTION] "
                    f"Processing {job.platform} job "
                    f"for streamer {job.streamer}."
                )

                result = await adapter.redeem(job)

                print(
                    "[REDEMPTION] "
                    f"Result: {result.status}"
                )

                if result.message:
                    print(
                        "[REDEMPTION] Adapter returned an additional message."
                    )

                if result.status == "RATE_LIMITED":
                    # Clear the event before the next iteration.
                    # The next job will remain in the queue.
                    self._resume_event.clear()

                    print(
                        "[REDEMPTION] RATE LIMIT DETECTED. "
                        "Processing is paused. Investigate the "
                        "rate limit before explicitly resuming."
                    )

                elif result.status == "UNKNOWN":
                    print(
                        "[REDEMPTION] Outcome is uncertain. "
                        "This job will not be automatically retried."
                    )

            except asyncio.CancelledError:
                raise


            except Exception:

                print(

                    "[REDEMPTION] Unexpected error while processing "

                    f"{job.platform} job for streamer {job.streamer}."

                )

            finally:
                # Mark only the job we actually retrieved as done.
                self.queue.task_done()