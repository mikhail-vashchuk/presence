SILENCE = "silence"
BALANCE = "balance"


class HintPolicy:
    """Decides when the assistant may speak.

    It stays silent by default. A hint is allowed only after a long pause or
    a long one-sided stretch, and never more often than the cooldown, which
    doubles every time a hint is dismissed with "not now".
    """

    def __init__(
            self,
            *,
            startup_grace,
            silence_after,
            balance_share,
            balance_window,
            balance_min_speech,
            cooldown,
            max_cooldown,
    ):
        self._startup_grace = startup_grace
        self._silence_after = silence_after
        self._balance_share = balance_share
        self._balance_window = balance_window
        self._balance_min_speech = balance_min_speech
        self._base_cooldown = cooldown
        self._max_cooldown = max_cooldown
        self._cooldown = cooldown
        self._last_hint_at = None

    @property
    def cooldown(self):
        return self._cooldown

    def decide(self, conversation, now):
        if now - conversation.started_at < self._startup_grace:
            return None

        if (
                self._last_hint_at is not None
                and now - self._last_hint_at < self._cooldown
        ):
            return None

        if conversation.silence(now) >= self._silence_after:
            return SILENCE

        talk = conversation.talk_seconds(now, self._balance_window)
        total = sum(talk.values())

        if (
                total >= self._balance_min_speech
                and max(talk.values()) / total >= self._balance_share
        ):
            return BALANCE

        return None

    def hint_sent(self, now):
        self._last_hint_at = now

    def hint_dismissed(self):
        self._cooldown = min(
            self._cooldown * 2,
            self._max_cooldown,
        )
