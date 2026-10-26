from unittest import IsolatedAsyncioTestCase

import httpx

from assistant.backend import Backend


class BackendTests(IsolatedAsyncioTestCase):
    def make_backend(self, handler):
        client = httpx.AsyncClient(
            base_url="http://backend/api/presence",
            headers={"Authorization": "Bearer secret"},
            transport=httpx.MockTransport(handler),
        )

        return Backend(base_url="", token="", client=client)

    async def test_get_session(self):
        requests = []

        def handler(request):
            requests.append(request)

            return httpx.Response(200, json={"active": True})

        session = await self.make_backend(handler).get_session(7)

        self.assertEqual(session, {"active": True})
        self.assertEqual(
            requests[0].url.path,
            "/api/presence/internal/moments/7/assistant/",
        )
        self.assertEqual(
            requests[0].headers["Authorization"],
            "Bearer secret",
        )

    async def test_record_hint(self):
        requests = []

        def handler(request):
            requests.append(request)

            return httpx.Response(201, json={"hint_id": 5})

        hint_id = await self.make_backend(handler).record_hint(7, "silence")

        self.assertEqual(hint_id, 5)
        self.assertEqual(
            requests[0].url.path,
            "/api/presence/internal/moments/7/assistant-hints/",
        )
        self.assertEqual(requests[0].content, b'{"kind":"silence"}')

    async def test_an_error_response_raises(self):
        backend = self.make_backend(lambda request: httpx.Response(403))

        with self.assertRaises(httpx.HTTPStatusError):
            await backend.get_session(7)
