from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Utterance:
    speaker: str
    text: str


class Conversation:
    """What the assistant knows about the conversation so far.

    It lives only in memory for the duration of one Moment. Speakers are
    anonymous labels, never identities.
    """

    def __init__(self, *, started_at, max_chars=60_000):
        self._started_at = started_at
        self._max_chars = max_chars
        self._utterances = deque()
        self._chars = 0
        self._speaking = {}
        self._spans = deque()
        self._last_speech_end = None

    @property
    def started_at(self):
        return self._started_at

    def add_utterance(self, speaker, text):
        text = text.strip()

        if not text:
            return

        self._utterances.append(Utterance(speaker, text))
        self._chars += len(text)

        while self._chars > self._max_chars and self._utterances:
            dropped = self._utterances.popleft()
            self._chars -= len(dropped.text)

    def speech_started(self, speaker, at):
        self._speaking.setdefault(speaker, at)

    def speech_ended(self, speaker, at):
        started = self._speaking.pop(speaker, None)

        if started is None:
            return

        self._spans.append((speaker, started, at))
        self._last_speech_end = at

    def is_anyone_speaking(self):
        return bool(self._speaking)

    def silence(self, now):
        if self.is_anyone_speaking():
            return 0.0

        last_activity = (
            self._last_speech_end
            if self._last_speech_end is not None
            else self._started_at
        )

        return max(0.0, now - last_activity)

    def talk_seconds(self, now, window):
        since = now - window
        totals = {}

        for speaker, start, end in self._spans:
            overlap = min(end, now) - max(start, since)

            if overlap > 0:
                totals[speaker] = totals.get(speaker, 0.0) + overlap

        for speaker, start in self._speaking.items():
            overlap = now - max(start, since)

            if overlap > 0:
                totals[speaker] = totals.get(speaker, 0.0) + overlap

        return totals

    def transcript(self):
        return "\n".join(
            f"{utterance.speaker}: {utterance.text}"
            for utterance in self._utterances
        )
