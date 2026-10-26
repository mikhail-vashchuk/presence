import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    backend_url: str
    service_token: str
    agent_name: str
    model: str
    stt_language: str
    poll_interval: float
    startup_grace: float
    silence_after: float
    balance_share: float
    balance_window: float
    balance_min_speech: float
    cooldown: float
    max_cooldown: float

    @classmethod
    def from_env(cls):
        return cls(
            backend_url=os.environ["ASSISTANT_BACKEND_URL"].rstrip("/"),
            service_token=os.environ["ASSISTANT_SERVICE_TOKEN"],
            agent_name=os.environ.get(
                "ASSISTANT_AGENT_NAME",
                "presence-assistant",
            ),
            model=os.environ.get(
                "ASSISTANT_MODEL",
                "claude-opus-5-5",
            ),
            stt_language=os.environ.get(
                "ASSISTANT_STT_LANGUAGE",
                "multi",
            ),
            poll_interval=float(
                os.environ.get("ASSISTANT_POLL_INTERVAL", "3"),
            ),
            startup_grace=float(
                os.environ.get("ASSISTANT_STARTUP_GRACE", "30"),
            ),
            silence_after=float(
                os.environ.get("ASSISTANT_SILENCE_AFTER", "25"),
            ),
            balance_share=float(
                os.environ.get("ASSISTANT_BALANCE_SHARE", "0.85"),
            ),
            balance_window=float(
                os.environ.get("ASSISTANT_BALANCE_WINDOW", "300"),
            ),
            balance_min_speech=float(
                os.environ.get("ASSISTANT_BALANCE_MIN_SPEECH", "90"),
            ),
            cooldown=float(
                os.environ.get("ASSISTANT_COOLDOWN", "180"),
            ),
            max_cooldown=float(
                os.environ.get("ASSISTANT_MAX_COOLDOWN", "1200"),
            ),
        )
