import httpx


class Backend:
    """The assistant's only connection to the Presence backend."""

    def __init__(self, *, base_url, token, client=None):
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    async def get_session(self, moment_id):
        response = await self._client.get(
            f"/internal/moments/{moment_id}/assistant/",
        )
        response.raise_for_status()

        return response.json()

    async def record_hint(self, moment_id, kind):
        response = await self._client.post(
            f"/internal/moments/{moment_id}/assistant-hints/",
            json={"kind": kind},
        )
        response.raise_for_status()

        return response.json()["hint_id"]

    async def aclose(self):
        await self._client.aclose()
