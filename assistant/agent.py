import asyncio
import json
import logging
import time

import anthropic

from livekit import rtc
from livekit.agents import (
    AgentServer,
    AutoSubscribe,
    JobContext,
    cli,
    stt,
)
from livekit.plugins import deepgram

from assistant.backend import Backend
from assistant.config import Settings
from assistant.conversation import Conversation
from assistant.hints import HintWriter
from assistant.policy import HintPolicy
from assistant.session import HINT_TOPIC, Assistant


logger = logging.getLogger(__name__)

settings = Settings.from_env()
server = AgentServer()


def speaker_labels():
    labels = {}

    def label(identity):
        if identity not in labels:
            labels[identity] = chr(ord("A") + len(labels))

        return labels[identity]

    return label


async def transcribe(track, speaker, conversation, speech_to_text):
    """Turns one participant's audio into events on the conversation.

    Audio is streamed to the speech-to-text provider and discarded; only the
    recognised text is kept, in memory.
    """
    audio = rtc.AudioStream.from_track(
        track=track,
        sample_rate=16000,
        num_channels=1,
    )
    stream = speech_to_text.stream()

    async def push():
        async for event in audio:
            stream.push_frame(event.frame)

        stream.end_input()

    pusher = asyncio.create_task(push())

    try:
        async for event in stream:
            if event.type == stt.SpeechEventType.START_OF_SPEECH:
                conversation.speech_started(speaker, time.monotonic())

            elif event.type == stt.SpeechEventType.END_OF_SPEECH:
                conversation.speech_ended(speaker, time.monotonic())

            elif (
                    event.type == stt.SpeechEventType.FINAL_TRANSCRIPT
                    and event.alternatives
            ):
                conversation.add_utterance(
                    speaker,
                    event.alternatives[0].text,
                )
    finally:
        pusher.cancel()
        conversation.speech_ended(speaker, time.monotonic())
        await stream.aclose()
        await audio.aclose()


@server.rtc_session(agent_name=settings.agent_name)
async def entrypoint(ctx: JobContext):
    moment_id = json.loads(ctx.job.metadata)["moment_id"]

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    room = ctx.room
    me = room.local_participant.identity

    # A second dispatch can race the first one; only one assistant stays.
    if any(
            participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
            and participant.identity < me
            for participant in room.remote_participants.values()
    ):
        ctx.shutdown("another assistant is already in the room")
        return

    backend = Backend(
        base_url=settings.backend_url,
        token=settings.service_token,
    )
    conversation = Conversation(started_at=time.monotonic())
    assistant = Assistant(
        moment_id=moment_id,
        conversation=conversation,
        policy=HintPolicy(
            startup_grace=settings.startup_grace,
            silence_after=settings.silence_after,
            balance_share=settings.balance_share,
            balance_window=settings.balance_window,
            balance_min_speech=settings.balance_min_speech,
            cooldown=settings.cooldown,
            max_cooldown=settings.max_cooldown,
        ),
        backend=backend,
        writer=HintWriter(
            client=anthropic.AsyncAnthropic(),
            model=settings.model,
        ),
        publish=lambda payload: room.local_participant.publish_data(
            payload,
            reliable=True,
            topic=HINT_TOPIC,
        ),
    )

    # Conversations are private: never let the provider train on them.
    speech_to_text = deepgram.STT(
        model="nova-3",
        language=settings.stt_language,
        mip_opt_out=True,
    )
    label = speaker_labels()
    listeners = {}

    def listen(track, participant):
        if (
                track.kind != rtc.TrackKind.KIND_AUDIO
                or participant.kind != rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD
                or participant.identity in listeners
        ):
            return

        listeners[participant.identity] = asyncio.create_task(
            transcribe(
                track,
                label(participant.identity),
                conversation,
                speech_to_text,
            )
        )

    def on_track_subscribed(track, publication, participant):
        listen(track, participant)

    def on_track_unsubscribed(track, publication, participant):
        task = listeners.pop(participant.identity, None)

        if task is not None:
            task.cancel()

    room.on("track_subscribed", on_track_subscribed)
    room.on("track_unsubscribed", on_track_unsubscribed)

    for participant in room.remote_participants.values():
        for publication in participant.track_publications.values():
            if publication.track is not None:
                listen(publication.track, participant)

    disconnected = asyncio.Event()
    room.on("disconnected", lambda *_: disconnected.set())

    try:
        while not disconnected.is_set():
            if not await assistant.tick(time.monotonic()):
                break

            try:
                await asyncio.wait_for(
                    disconnected.wait(),
                    timeout=settings.poll_interval,
                )
            except asyncio.TimeoutError:
                pass
    finally:
        for task in listeners.values():
            task.cancel()

        await backend.aclose()
        await room.disconnect()


if __name__ == "__main__":
    cli.run_app(server)
