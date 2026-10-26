from unittest import TestCase

from assistant.conversation import Conversation
from assistant.policy import BALANCE, SILENCE, HintPolicy


def make_policy(**overrides):
    options = {
        "startup_grace": 30,
        "silence_after": 25,
        "balance_share": 0.85,
        "balance_window": 300,
        "balance_min_speech": 90,
        "cooldown": 180,
        "max_cooldown": 1200,
    }
    options.update(overrides)

    return HintPolicy(**options)


def speak(conversation, speaker, start, end):
    conversation.speech_started(speaker, start)
    conversation.speech_ended(speaker, end)


class HintPolicyTests(TestCase):
    def setUp(self):
        self.conversation = Conversation(started_at=0)
        self.policy = make_policy()

    def test_stays_silent_during_the_startup_grace(self):
        self.assertIsNone(self.policy.decide(self.conversation, now=20))

    def test_offers_a_hint_after_a_long_silence(self):
        speak(self.conversation, "A", 10, 60)
        speak(self.conversation, "B", 60, 100)

        self.assertEqual(
            self.policy.decide(self.conversation, now=130),
            SILENCE,
        )

    def test_offers_a_hint_when_nobody_ever_spoke(self):
        self.assertEqual(
            self.policy.decide(self.conversation, now=40),
            SILENCE,
        )

    def test_stays_silent_during_a_short_pause(self):
        speak(self.conversation, "A", 10, 60)
        speak(self.conversation, "B", 60, 100)

        self.assertIsNone(self.policy.decide(self.conversation, now=110))

    def test_offers_a_hint_when_one_voice_dominates(self):
        speak(self.conversation, "A", 0, 100)
        speak(self.conversation, "B", 100, 105)

        self.assertEqual(
            self.policy.decide(self.conversation, now=106),
            BALANCE,
        )

    def test_stays_silent_when_the_talk_is_shared(self):
        speak(self.conversation, "A", 0, 60)
        speak(self.conversation, "B", 60, 120)

        self.assertIsNone(self.policy.decide(self.conversation, now=121))

    def test_does_not_judge_balance_on_too_little_speech(self):
        speak(self.conversation, "A", 0, 40)

        self.assertIsNone(self.policy.decide(self.conversation, now=41))

    def test_waits_for_the_cooldown_between_hints(self):
        self.policy.hint_sent(now=40)

        self.assertIsNone(self.policy.decide(self.conversation, now=200))
        self.assertEqual(
            self.policy.decide(self.conversation, now=221),
            SILENCE,
        )

    def test_dismissing_a_hint_doubles_the_cooldown(self):
        self.policy.hint_dismissed()

        self.assertEqual(self.policy.cooldown, 360)

    def test_the_cooldown_has_a_ceiling(self):
        for _ in range(10):
            self.policy.hint_dismissed()

        self.assertEqual(self.policy.cooldown, 1200)
