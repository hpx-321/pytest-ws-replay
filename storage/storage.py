import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from model.types import CassetteData


class CassetteStorage:
    """Handles storage and retrieval of WebSocket recordings."""

    def __init__(self, base_dir: str = "cassette/websocket_recording", project_root: Optional[str] = None):
        """Initialize storage with base directory."""
        current_file = Path(__file__).resolve()

        if project_root:
            self.project_root = Path(project_root)
        else:
            # Default to parent directory of this module
            self.project_root = current_file.parent.parent

        self.base_dir = self.project_root / base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, query: str) -> str:
        """Sanitize query to create a safe filename."""
        try:
            if "\\u" in query:
                query = query.encode('utf-8').decode('unicode_escape')

        except Exception as e:
            print(f"[CassetteStorage] Unicode处理错误: {e}")

        # Remove or replace characters that are not safe for filenames
        safe_query = re.sub(r'[<>:"/\\|?*]', '_', query)
        # Remove leading/trailing whitespace and dots
        safe_query = safe_query.strip('. ')

        return safe_query

    def find_cassette(self, query: str) -> Optional[Path]:
        """Find existing cassette file for the given query."""
        safe_query = self._sanitize_filename(query)

        # Check in stable directory first
        stable_file = self.base_dir / "stable" / f"ws_{safe_query}.json"
        if stable_file.exists():
            print(f"[CassetteStorage] 在stable目录找到文件: {stable_file}")
            return stable_file

        return None

    def get_save_path(self, query: str) -> Path:
        """Get the path where a new recording should be saved."""
        now_utc = datetime.now(timezone.utc)
        today = now_utc.strftime("%Y-%m-%d")
        save_dir = self.base_dir / today
        save_dir.mkdir(parents=True, exist_ok=True)

        safe_query = self._sanitize_filename(query)
        return save_dir / f"ws_{safe_query}.json"

    def load(self, path: Path) -> Dict[str, Any]:
        """Load cassette data from file."""
        if not path or not path.exists():
            raise FileNotFoundError(f"录音带文件不存在: {path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except json.JSONDecodeError as e:
            print(f"[CassetteStorage] JSON解析错误: {e}")
            raise
        except Exception as e:
            print(f"[CassetteStorage] 读取数据出现错误，错误类型: {e}")
            raise

    def save(self, query: str, data):
        """Save cassette data to file."""
        path = self.get_save_path(query)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[CassetteStorage] 录制文件已经保存到: {path}")

        except Exception as e:
            print(f"[CassetteStorage] 保存数据时出现错误: {e}")
            raise