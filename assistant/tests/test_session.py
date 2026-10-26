import json
from unittest import IsolatedAsyncioTestCase

import httpx

from assistant.conversation import Conversation
from assistant.policy import SILENCE, HintPolicy
from assistant.session import Assistant


class FakeBackend:
    def __init__(self):
        self.session = {
            "active": True,
            "gesture": "gesture",
            "words": "words",
            "dismissed_hint_ids": [],
        }
        self.fail = False
        self.recorded = []
        self.next_hint_id = 1

    async def get_session(self, moment_id):
        if self.fail:
            raise httpx.ConnectError("down")

        return self.session

    async def record_hint(self, moment_id, kind):
        self.recorded.append((moment_id, kind))
        hint_id = self.next_hint_id
        self.next_hint_id += 1

        return hint_id


class FakeWriter:
    def __init__(self, text="What changed?"):
        self.text = text
        self.calls = []

    async def write(self, **kwargs):
        self.calls.append(kwargs)

        return self.text


class AssistantTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.writer = FakeWriter()
        self.published = []
        self.conversation = Conversation(started_at=0)
        self.policy = HintPolicy(
            startup_grace=30,
            silence_after=25,
            balance_share=0.85,
            balance_window=300,
            balance_min_speech=90,
            cooldown=180,
            max_cooldown=1200,
        )
        self.assistant = Assistant(
            moment_id=7,
            conversation=self.conversation,
            policy=self.policy,
            backend=self.backend,
            writer=self.writer,
            publish=self.publish,
        )

    async def publish(self, payload):
        self.published.append(json.loads(payload))

    async def test_publishes_a_hint_after_a_silence(self):
        self.assertTrue(await self.assistant.tick(now=60))

        self.assertEqual(self.backend.recorded, [(7, SILENCE)])
        self.assertEqual(
            self.published,
            [{"hint_id": 1, "text": "What changed?"}],
        )

    async def test_the_writer_gets_the_reason_for_the_meeting(self):
        await self.assistant.tick(now=60)

        self.assertEqual(self.writer.calls[0]["gesture"], "gesture")
        self.assertEqual(self.writer.calls[0]["words"], "words")

    async def test_stays_silent_when_it_is_too_early(self):
        await self.assistant.tick(now=10)

        self.assertEqual(self.published, [])
        self.assertEqual(self.writer.calls, [])

    async def test_stays_silent_while_someone_is_speaking(self):
        self.conversation.speech_started("A", 55)

        await self.assistant.tick(now=60)

        self.assertEqual(self.published, [])

    async def test_leaves_when_consent_is_withdrawn(self):
        self.backend.session["active"] = False

        self.assertFalse(await self.assistant.tick(now=60))
        self.assertEqual(self.published, [])

    async def test_leaves_after_repeated_failures_to_check_consent(self):
        self.backend.fail = True

        self.assertTrue(await self.assistant.tick(now=60))
        self.assertTrue(await self.assistant.tick(now=63))
        self.assertFalse(await self.assistant.tick(now=66))

    async def test_a_successful_check_resets_the_failure_count(self):
        self.backend.fail = True
        await self.assistant.tick(now=60)
        await self.assistant.tick(now=63)
        self.backend.fail = False
        await self.assistant.tick(now=66)
        self.backend.fail = True

        self.assertTrue(await self.assistant.tick(now=69))

    async def test_dismissing_a_hint_backs_off(self):
        await self.assistant.tick(now=60)
        self.backend.session["dismissed_hint_ids"] = [1]

        await self.assistant.tick(now=63)
        await self.assistant.tick(now=66)

        self.assertEqual(self.policy.cooldown, 360)

    async def test_a_hint_the_assistant_did_not_make_is_ignored(self):
        self.backend.session["dismissed_hint_ids"] = [99]

        await self.assistant.tick(now=10)

        self.assertEqual(self.policy.cooldown, 180)

    async def test_no_hint_text_means_nothing_is_recorded(self):
        self.writer.text = None

        await self.assistant.tick(now=60)

        self.assertEqual(self.backend.recorded, [])
        self.assertEqual(self.published, [])

    async def test_a_skipped_attempt_still_starts_the_cooldown(self):
        self.writer.text = None

        await self.assistant.tick(now=60)
        await self.assistant.tick(now=63)

        self.assertEqual(len(self.writer.calls), 1)

    async def test_earlier_hints_are_passed_to_the_writer(self):
        await self.assistant.tick(now=60)
        await self.assistant.tick(now=300)

        self.assertEqual(
            self.writer.calls[1]["earlier_hints"],
            ["What changed?"],
        )
