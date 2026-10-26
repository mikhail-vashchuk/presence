"""Plays a Moment between two simulated people so the assistant can be seen working.

Run the backend and the assistant first, in two terminals. The demo
thresholds make the assistant speak after seconds instead of minutes:

    python manage.py runserver

    ASSISTANT_POLL_INTERVAL=1 ASSISTANT_STARTUP_GRACE=5 \\
    ASSISTANT_SILENCE_AFTER=10 ASSISTANT_BALANCE_MIN_SPEECH=40 \\
    python -m assistant.agent dev

Then, in a third one:

    python -m scripts.demo_moment                      # a conversation that falls silent
    python -m scripts.demo_moment --scenario balance   # one person does all the talking

The script walks the real domain flow (Invitation, Response, acceptance), joins
the media room as both people, asks for the assistant on behalf of both, speaks
scripted lines with Deepgram voices and prints the hint the assistant sends.
It writes to the development database and completes the Moment when it is done.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from livekit import rtc  # noqa: E402
from livekit.plugins import deepgram  # noqa: E402

from accounts.models import User  # noqa: E402

from humans.models import Human  # noqa: E402

from presence.models import AssistantHint  # noqa: E402
from presence.selectors import get_current_presence_state  # noqa: E402
from presence.services import (  # noqa: E402
    accept_response,
    cancel_response,
    close_invitation,
    complete_moment,
    create_invitation,
    create_moment_media_access,
    dismiss_assistant_hint,
    send_response,
    set_agent_consent,
)


HINT_TOPIC = "assistant.hint"

GESTURE = "I keep abandoning side projects and I want to understand why."
WORDS = "Same here. I dropped my third one last week."

SILENCE_SCRIPT = [
    ("A", "Hi! I saw your reply. I keep starting side projects and then "
          "abandoning them, and I want to understand why."),
    ("B", "Same here, honestly. I dropped my third one just last week."),
    ("A", "What usually makes you stop? For me it is the moment the fun "
          "part is over and the boring work begins."),
    ("B", "Yes, exactly. The boring part feels like a completely different "
          "job."),
]

BALANCE_SCRIPT = [
    ("A", "Hi! I saw your reply. Let me tell you how it usually goes for "
          "me."),
    ("B", "Sure, go ahead."),
    ("A", "I start with a lot of energy. I read everything, I sketch the "
          "design, I tell my friends about it. The first weekend is "
          "wonderful."),
    ("A", "Then the second week comes, and the first real problem shows "
          "up. It is never a big problem. It is a small, boring one, like "
          "a configuration file that refuses to work."),
    ("A", "I fix it, but the excitement has gone. The next day I open the "
          "project and feel nothing, so I open something new instead."),
    ("A", "And the new thing is exciting, of course, because it has no "
          "boring parts yet. That is the trap I keep walking into, again "
          "and again, and I honestly do not know how to get out of it."),
]

VOICES = {
    "A": "aura-2-andromeda-en",
    "B": "aura-2-apollo-en",
}

SAMPLE_RATE = 24000


def say(message):
    print(message, flush=True)


def get_or_create_human(*, email, first_name):
    user, _ = User.objects.get_or_create(email=email)
    human, _ = Human.objects.get_or_create(
        user=user,
        defaults={"first_name": first_name, "last_name": "Demo"},
    )

    return human


def clear_state(human):
    """Leaves the Human idle, using the same services the API uses."""
    state = get_current_presence_state(human_id=human.pk)

    if state["state"] == "moment":
        complete_moment(human_id=human.pk, moment_id=state["moment"].pk)
    elif state["state"] == "invitation":
        close_invitation(
            human_id=human.pk,
            invitation_id=state["invitation"].pk,
        )
    elif state["state"] == "response":
        cancel_response(
            human_id=human.pk,
            response_id=state["response"].pk,
        )


def start_moment():
    inviter = get_or_create_human(email="demo-a@example.com", first_name="Ada")
    responder = get_or_create_human(email="demo-b@example.com", first_name="Bo")

    clear_state(inviter)
    clear_state(responder)

    invitation = create_invitation(human_id=inviter.pk, gesture=GESTURE)
    response = send_response(
        human_id=responder.pk,
        invitation_id=invitation.pk,
        words=WORDS,
    )
    moment = accept_response(human_id=inviter.pk, response_id=response.pk)

    return moment, {
        "A": inviter,
        "B": responder,
    }


class Participant:
    def __init__(self, name, tts):
        self.name = name
        self.room = rtc.Room()
        self._tts = tts
        self._source = rtc.AudioSource(SAMPLE_RATE, 1)
        self.hints = asyncio.Queue()
        self.assistant_joined = asyncio.Event()

        self.room.on("data_received", self._on_data)
        self.room.on("participant_connected", self._on_participant)

    def _on_participant(self, participant):
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            self.assistant_joined.set()

    def _on_data(self, packet):
        if packet.topic == HINT_TOPIC:
            self.hints.put_nowait(packet.data.decode())

    async def join(self, access):
        await self.room.connect(
            access["server_url"],
            access["participant_token"],
        )

        track = rtc.LocalAudioTrack.create_audio_track(
            "microphone",
            self._source,
        )
        await self.room.local_participant.publish_track(
            track,
            rtc.TrackPublishOptions(
                source=rtc.TrackSource.SOURCE_MICROPHONE,
            ),
        )

        for participant in self.room.remote_participants.values():
            self._on_participant(participant)

    async def speak(self, text):
        say(f"  {self.name}: {text}")

        async for audio in self._tts.synthesize(text):
            await self._source.capture_frame(audio.frame)

        await self._source.wait_for_playout()


async def play(moment, humans, accesses, scenario, wait):
    script = SILENCE_SCRIPT if scenario == "silence" else BALANCE_SCRIPT
    participants = {
        name: Participant(
            name,
            deepgram.TTS(model=VOICES[name], sample_rate=SAMPLE_RATE),
        )
        for name in humans
    }

    try:
        say("Joining the room as both people...")
        await asyncio.gather(
            *(participants[name].join(accesses[name]) for name in humans)
        )

        say("Both people agree to the quiet assistant...")
        for name, human in humans.items():
            await asyncio.to_thread(
                set_agent_consent,
                human_id=human.pk,
                moment_id=moment.pk,
                consent=True,
            )

        say("Waiting for the assistant to join (is `python -m assistant.agent dev` running?)...")
        try:
            await asyncio.wait_for(
                participants["A"].assistant_joined.wait(),
                timeout=30,
            )
        except asyncio.TimeoutError:
            say("The assistant did not join within 30 seconds.")
            return

        say("The assistant is in the room. The conversation begins:")
        for name, text in script:
            await participants[name].speak(text)
            await asyncio.sleep(2.5)

        say(f"Now it is quiet. Waiting up to {wait} seconds for a hint...")
        try:
            payload = await asyncio.wait_for(
                participants["B"].hints.get(),
                timeout=wait,
            )
        except asyncio.TimeoutError:
            say("No hint arrived. Check the assistant's output.")
            return

        say(f"\nHint received: {payload}\n")

        hint = await asyncio.to_thread(
            lambda: AssistantHint.objects.filter(moment=moment).last()
        )
        say(f"Recorded in the database as a '{hint.kind}' hint.")

        await asyncio.to_thread(
            dismiss_assistant_hint,
            human_id=humans["B"].pk,
            hint_id=hint.pk,
        )
        say('B pressed "not now"; the assistant will wait twice as long.')
    finally:
        for participant in participants.values():
            await participant.room.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--scenario",
        choices=["silence", "balance"],
        default="silence",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=90,
        help="seconds to wait for a hint after the conversation",
    )
    args = parser.parse_args()

    moment, humans = start_moment()
    say(f"Moment #{moment.pk} started between two demo people.")

    accesses = {
        name: create_moment_media_access(
            human_id=human.pk,
            moment_id=moment.pk,
        )
        for name, human in humans.items()
    }

    try:
        asyncio.run(play(moment, humans, accesses, args.scenario, args.wait))
    finally:
        complete_moment(human_id=humans["A"].pk, moment_id=moment.pk)
        say("Moment completed.")


if __name__ == "__main__":
    main()
