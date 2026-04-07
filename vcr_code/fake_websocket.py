import json
from typing import List, Any, Optional
from model.types import Interaction


class FakeWebSocket:
    """Fake WebSocket that plays back recorded interactions."""

    def __init__(self, interactions: List[Interaction], target_url: str, parent_vcr: Any):
        self.interactions = interactions
        self.parent_vcr = parent_vcr
        self.target_url = target_url
        self.closed = False
        self.current_response = []

        # WebSocket-like attributes
        self.id = f"fake_ws_{id(self)}"
        self.remote_address = ("127.0.0.1", 8000)
        self.state = 'OPEN'
        self.local_address = ("127.0.0.1", 54321)

    async def send(self, message: str):
        """Simulate sending a message (no-op in playback mode)."""
        idx = self.parent_vcr.playback_interaction_indices.get(self.target_url, 0)

        if idx < len(self.interactions):
            interaction = self.interactions[idx]
            self.current_response = interaction.get('response' ,[])
            self.parent_vcr.playback_interaction_indices[self.target_url] = idx + 1
        else:
            print(f"[FakeWebSocket] 回放数据不足，当前请求url为 {self.target_url}")
            self.current_response =[]

    async def recv(self) -> Optional[str]:

        if not self.current_response:
            print("[FakeWebSocket] 没有回放数据")
            return None

        chunk = self.current_response.pop(0)
        if isinstance(chunk, dict):
            return json.dumps(chunk, ensure_ascii=False)

        return str(chunk)

    async def close(self):
        """Close the fake WebSocket."""
        self.closed = True
        self.state = "CLOSED"

    def __aiter__(self):
        """Support async iteration."""
        return self

    async def __anext__(self):
        """Support async for loop."""
        if self.closed:
            raise StopAsyncIteration

        try:
            data = await self.recv()
            return data
        except Exception as e:
            print(f"[FakeWebSocket] 出现报错，错误原因{e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def send_text(self, message: str):
        """Send text message (alias for send)."""
        await self.send(message)

    def __str__(self):
        return f"FakeWebSocket(target_url={self.target_url}, state={self.state})"