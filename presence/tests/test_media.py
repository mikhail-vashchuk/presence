from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase, override_settings

from presence.media import dispatch_assistant


@override_settings(
    LIVEKIT_URL="http://livekit.test",
    LIVEKIT_API_KEY="key",
    LIVEKIT_API_SECRET="secret",
    ASSISTANT_AGENT_NAME="test-assistant",
)
class DispatchAssistantTests(SimpleTestCase):
    @patch("presence.media.api.LiveKitAPI")
    def test_dispatch_assistant_asks_for_the_named_agent(self, livekit_api):
        create_dispatch = AsyncMock()
        livekit = livekit_api.return_value.__aenter__.return_value
        livekit.agent_dispatch.create_dispatch = create_dispatch

        dispatch_assistant(
            room_id="room-1",
            moment_id=7,
        )

        request = create_dispatch.await_args.args[0]

        self.assertEqual(request.agent_name, "test-assistant")
        self.assertEqual(request.room, "room-1")
        self.assertEqual(request.metadata, '{"moment_id": 7}')

    @patch("presence.media.api.LiveKitAPI")
    def test_dispatch_assistant_does_not_raise_when_livekit_fails(self, livekit_api):
        livekit_api.side_effect = RuntimeError("down")

        with self.assertLogs("presence.media", level="ERROR"):
            dispatch_assistant(
                room_id="room-1",
                moment_id=7,
            )
