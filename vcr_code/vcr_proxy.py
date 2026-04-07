import asyncio
import websockets
import json
from typing import Dict, Optional, Any, List, Union
from datetime import datetime

from model.types import Interaction, CassetteData
from storage.storage import CassetteStorage
from .matcher import Matcher
from .fake_websocket import FakeWebSocket
from model.config import VCRConfig, MatcherConfig


class VCRProxy:
    """Main proxy class that intercepts WebSocket connections."""

    def __init__(self):
        self.mode: str = 'idle'
        self.storage: Optional[CassetteStorage] = None
        self.query: Optional[str] = None
        self.original_connect = websockets.connect


        # Recording components
        self.recorder: Optional['Recorder'] = None

        # Playback components
        self.player: Optional['Player'] = None
        self.matcher: Optional[Matcher] = None

        self.playback_interaction_indices: Dict[str, int] = {}

    def set_record_mode(self, query: str, storage: CassetteStorage):
        """Switch to recording mode."""
        self.mode = 'record'
        self.query = query
        self.storage = storage
        self.recorder = Recorder(self)
        self.player = None
        print("[VCRProxy] 切换到录制模式")

    def set_playback_mode(self, query: str, storage: CassetteStorage, data: Dict[str, List[Interaction]]):
        """Switch to playback mode."""
        self.mode = 'playback'
        self.query = query
        self.storage = storage
        self.player = Player(self)
        self.player.load_playback_data(data)
        self.recorder = None
        self.matcher = Matcher(self)
        print("[VCRProxy] 切换到回放模式")

    async def intercept(self, *args, **kwargs):
        """Intercept WebSocket connections."""
        target_url = args[0] if args else kwargs.get("url", "")

        if self.mode == 'playback' and self.player:
            return self.player.create_fake_websocket(target_url, self.matcher)

        elif self.mode == 'record' and self.recorder:
            return await self.recorder.record_connection(
                self.original_connect, *args, **kwargs
            )

        else:
            return await self.original_connect(*args, **kwargs)

    def _has_requirements(self) -> bool:
        """Check if all requirements for recording are met."""
        return (
            self.mode == 'record'
            and bool(self.recorder)
            and bool(self.query)
            and bool(self.storage)
        )

    def save_recording(self):
        """Save recorded data."""
        if self._has_requirements():
            self.recorder.save_recording(self.query, self.storage)

    def cleanup(self):
        """Clean up resources."""
        if self.recorder:
            self.recorder.cleanup()
        self.mode = 'idle'
        self.playback_interaction_indices.clear()


class Recorder:
    """Handles recording of WebSocket connections."""

    def __init__(self, vcr_proxy: VCRProxy):
        self.vcr_proxy = vcr_proxy
        self.all_recorded_data: Dict[str, List[Interaction]] = {}
        self.active_connections: List[Any] = []

    async def record_connection(self, original_connect, *args, **kwargs):
        """Record a WebSocket connection."""
        target_url = args[0] if args else kwargs.get("url", "")
        ws = await original_connect(*args, **kwargs)

        original_recv = ws.recv
        original_send = ws.send

        current_interaction = None

        async def hooked_send(message):
            await original_send(message)

            # Check if it's a heartbeat message
            is_heartbeat = False
            try:
                if isinstance(message, str):
                    msg_obj = json.loads(message)
                    if msg_obj.get('type') == 'ping':
                        is_heartbeat = True
            except Exception:
                pass

            if is_heartbeat:
                return

            nonlocal current_interaction

            # Create new interaction for sent message
            current_interaction = self._create_interaction(
                target_url, message, None
            )
        async def hooked_recv():
            """Handle receiving messages."""
            nonlocal current_interaction
            chunk = await original_recv()

            if current_interaction is not None:
                current_interaction["response"].append(chunk)
            else:
                self._create_interaction(target_url, None, chunk)

            return chunk

        ws.recv = hooked_recv
        ws.send = hooked_send

        return ws

    def _create_interaction(self, target_url: str, request: Optional[str], response: Optional[str]):
        """Create a new interaction entry."""
        if target_url not in self.all_recorded_data:
            self.all_recorded_data[target_url] = []

        interaction: Interaction = {
            "request": request,
            "response": [response] if response else []
        }

        self.all_recorded_data[target_url].append(interaction)
        return interaction

    def save_recording(self, query: str, storage: CassetteStorage):
        """Save recorded data to storage."""
        if self.all_recorded_data:
            print("[Recorder] 录制完成，准备保存数据")
            storage.save(query, self.all_recorded_data)

        self.active_connections.clear()

    def cleanup(self):
        """Clean up resources."""
        self.all_recorded_data.clear()
        self.active_connections.clear()


class Player:
    """Handles playback of recorded WebSocket sessions."""

    def __init__(self, vcr_proxy: VCRProxy):
        self.vcr_proxy = vcr_proxy
        self.playback_data: Dict[str, List[Interaction]] = {}
        self.playback_indices: Dict[str, int] = {}

    def load_playback_data(self, data: Dict[str, List[Interaction]]):
        """Load playback data."""
        self.playback_data = data
        self.playback_indices = {}

    def create_fake_websocket(self, target_url: str, matcher: Matcher) -> FakeWebSocket:
        """Create a fake WebSocket for playback."""
        matched_url = matcher.find_best_match(target_url, self.playback_data)
        interactions = self.playback_data.get(matched_url, [])

        if not interactions:
            print(f"[Player] 出现错误，当前请求url不存在数据记录: {target_url}")
            return FakeWebSocket([], target_url=target_url, parent_vcr=self.vcr_proxy)

        fake_ws = FakeWebSocket(interactions, matched_url, parent_vcr=self.vcr_proxy)
        return fake_ws


# Global instance for pytest integration
_vcr_instance = VCRProxy()
