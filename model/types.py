from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class WebsocketMessage:
    """Represents a single WebSocket message with metadata."""
    content: str
    timestamp: float
    direction: str  # 'send' or 'recv'
    message_type: str = 'text'  # 'text', 'binary', 'control'

    @property
    def is_control(self) -> bool:
        """Check if this is a control message (ping/pong/close)."""
        return self.message_type == 'control'


class Interaction(TypedDict):
    """Represents a single interaction in a WebSocket session."""
    request: Optional[str]  # Sent message
    response: List[str]  # Received responses


class CassetteData(TypedDict):
    """Represents the complete recording for a WebSocket URL."""
    url: str
    interactions: List[Interaction]
    created_at: str
    session_info: Dict[str, Any]


@dataclass
class PlaybackState:
    """Tracks the current state during playback."""
    url: str
    interaction_index: int = 0
    response_index: int = 0
    is_complete: bool = False

    def advance(self):
        """Move to the next interaction."""
        self.interaction_index += 1
        self.response_index = 0
        if self.interaction_index >= 10:  # Placeholder, should be actual max
            self.is_complete = True