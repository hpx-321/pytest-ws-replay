"""
Tests for Recorder class.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from vcr_code.vcr_proxy import Recorder
from storage.storage import CassetteStorage
from datetime import datetime


class TestRecorder:
    """Test Recorder class."""

    def test_recorder_init(self):
        """Test Recorder initialization."""
        proxy = MagicMock()
        recorder = Recorder(proxy)

        assert recorder.vcr_proxy == proxy
        assert recorder.all_recorded_data == {}
        assert recorder.active_connections == []

    def test_recorder_create_interaction(self):
        """Test _create_interaction creates proper structure."""
        proxy = MagicMock()
        recorder = Recorder(proxy)

        interaction = recorder._create_interaction(
            target_url="ws://example.com/test",
            request="Hello",
            response="World"
        )

        assert interaction["request"] == "Hello"
        assert interaction["response"] == ["World"]
        assert recorder.all_recorded_data == {
            'ws://example.com/test' :[{
            "request": 'Hello',
            "response": ["World"]
        }]
        }

    def test_recorder_create_interaction_with_null_request(self):
        """Test _create_interaction with null request."""
        proxy = MagicMock()
        recorder = Recorder(proxy)

        interaction = recorder._create_interaction(
            target_url="ws://example.com/test",
            request=None,
            response="Server push"
        )

        assert interaction["request"] is None
        assert interaction["response"] == ["Server push"]
        assert recorder.all_recorded_data == {
            'ws://example.com/test' :[{
            "request": None,
            "response": ["Server push"]
        }]
        }

    def test_recorder_create_interaction_multiple_urls(self):
        """Test recording interactions for multiple URLs."""
        proxy = MagicMock()
        recorder = Recorder(proxy)

        recorder._create_interaction("ws://example.com/chat", "msg1", "resp1")
        recorder._create_interaction("ws://example.com/updates", "msg2", "resp2")

        assert "ws://example.com/chat" in recorder.all_recorded_data
        assert "ws://example.com/updates" in recorder.all_recorded_data
        assert len(recorder.all_recorded_data["ws://example.com/chat"]) == 1
        assert len(recorder.all_recorded_data["ws://example.com/updates"]) == 1

    def test_recorder_save_recording(self):
        """Test save_recording calls storage.save."""
        proxy = MagicMock()
        recorder = Recorder(proxy)

        recorder._create_interaction("ws://example.com/test", "Hello", "World")

        storage = MagicMock()

        recorder.save_recording("ws://example.com/test", storage)

        storage.save.assert_called_once()
        assert recorder.active_connections == []

    def test_recorder_cleanup(self):
        """Test cleanup clears data."""
        proxy = MagicMock()
        recorder = Recorder(proxy)

        # Add some data
        recorder.all_recorded_data["ws://example.com/test"] = []
        recorder.active_connections = ["conn1", "conn2"]

        recorder.cleanup()

        assert recorder.all_recorded_data == {}
        assert recorder.active_connections == []
