import json
import logging

import httpx

from assistant.conversation import Conversation
from assistant.policy import HintPolicy


logger = logging.getLogger(__name__)

HINT_TOPIC = "assistant.hint"
MAX_FAILED_POLLS = 3


class Assistant:
    """One assistant for one Moment.

    It does not know about LiveKit. The agent feeds the conversation and calls
    `tick` periodically; `tick` returns False when the assistant must leave.
    """

    def __init__(
            self,
            *,
            moment_id,
            conversation: Conversation,
            policy: HintPolicy,
            backend,
            writer,
            publish,
    ):
        self.conversation = conversation
        self._moment_id = moment_id
        self._policy = policy
        self._backend = backend
        self._writer = writer
        self._publish = publish
        self._failed_polls = 0
        self._hints = {}
        self._handled_dismissals = set()

    async def tick(self, now):
        try:
            session = await self._backend.get_session(self._moment_id)
        except httpx.HTTPError:
            self._failed_polls += 1
            logger.warning(
                "Could not check consent (%s of %s)",
                self._failed_polls,
                MAX_FAILED_POLLS,
            )

            # Without a fresh answer the assistant cannot know that consent
            # still stands, so it leaves rather than keep listening.
            return self._failed_polls < MAX_FAILED_POLLS

        self._failed_polls = 0

        if not session["active"]:
            return False

        self._apply_dismissals(session["dismissed_hint_ids"])

        if self.conversation.is_anyone_speaking():
            return True

        kind = self._policy.decide(self.conversation, now)

        if kind is None:
            return True

        await self._offer_hint(kind, session, now)

        return True

    def _apply_dismissals(self, dismissed_hint_ids):
        for hint_id in dismissed_hint_ids:
            if (
                    hint_id in self._hints
                    and hint_id not in self._handled_dismissals
            ):
                self._handled_dismissals.add(hint_id)
                self._policy.hint_dismissed()

    async def _offer_hint(self, kind, session, now):
        text = await self._writer.write(
            kind=kind,
            gesture=session["gesture"],
            words=session["words"],
            transcript=self.conversation.transcript(),
            earlier_hints=list(self._hints.values()),
        )

        # A failed or skipped attempt still starts the cooldown, so the
        # assistant never retries in a tight loop.
        self._policy.hint_sent(now)

        if text is None:
            return

        try:
            hint_id = await self._backend.record_hint(
                self._moment_id,
                kind,
            )
        except httpx.HTTPError:
            logger.warning("Could not record a hint")
            return

        self._hints[hint_id] = text

        await self._publish(
            json.dumps(
                {
                    "hint_id": hint_id,
                    "text": text,
                }
            ),
        )
