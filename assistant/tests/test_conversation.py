from unittest import TestCase

from assistant.conversation import Conversation


class ConversationTests(TestCase):
    def setUp(self):
        self.conversation = Conversation(started_at=0)

    def test_silence_counts_from_the_start_when_nobody_spoke(self):
        self.assertEqual(self.conversation.silence(40), 40)

    def test_silence_counts_from_the_end_of_the_last_speech(self):
        self.conversation.speech_started("A", 5)
        self.conversation.speech_ended("A", 12)

        self.assertEqual(self.conversation.silence(40), 28)

    def test_there_is_no_silence_while_someone_speaks(self):
        self.conversation.speech_started("A", 5)

        self.assertTrue(self.conversation.is_anyone_speaking())
        self.assertEqual(self.conversation.silence(40), 0)

    def test_talk_seconds_per_speaker(self):
        self.conversation.speech_started("A", 0)
        self.conversation.speech_ended("A", 30)
        self.conversation.speech_started("B", 30)
        self.conversation.speech_ended("B", 40)

        self.assertEqual(
            self.conversation.talk_seconds(now=40, window=300),
            {"A": 30, "B": 10},
        )

    def test_talk_seconds_clips_to_the_window(self):
        self.conversation.speech_started("A", 0)
        self.conversation.speech_ended("A", 100)

        self.assertEqual(
            self.conversation.talk_seconds(now=150, window=100),
            {"A": 50},
        )

    def test_talk_seconds_counts_speech_in_progress(self):
        self.conversation.speech_started("A", 10)

        self.assertEqual(
            self.conversation.talk_seconds(now=25, window=300),
            {"A": 15},
        )

    def test_speech_ended_without_start_is_ignored(self):
        self.conversation.speech_ended("A", 10)

        self.assertEqual(self.conversation.silence(40), 40)

    def test_transcript_labels_speakers(self):
        self.conversation.add_utterance("A", "Hello")
        self.conversation.add_utterance("B", "  Hi there  ")
        self.conversation.add_utterance("A", "   ")

        self.assertEqual(
            self.conversation.transcript(),
            "A: Hello\nB: Hi there",
        )

    def test_transcript_drops_the_oldest_when_too_long(self):
        conversation = Conversation(started_at=0, max_chars=10)
        conversation.add_utterance("A", "first one")
        conversation.add_utterance("B", "second")

        self.assertEqual(conversation.transcript(), "B: second")
