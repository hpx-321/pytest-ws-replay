from typing import Dict, Optional, List


class Matcher:
    """Handles URL matching for playback."""

    def __init__(self, enable_fuzz_match: bool = True):
        """Initialize the matcher with fuzzy matching option."""
        self.enable_fuzzy_match = enable_fuzz_match

    def find_best_match(self, target_url: str, playback_data: Dict[str, List]) -> Optional[str]:
        """Find the best matching URL in playback data."""
        if target_url in playback_data:
            return target_url

        if self.enable_fuzzy_match:

            try:
                if '/' not in target_url:
                    return None

                target_path = self._extract_path(target_url)

                for recorded_url in playback_data.keys():
                    if '/' in recorded_url:
                        recorded_path = self._extract_path(recorded_url)
                        if target_path == recorded_path:
                            return recorded_url

            except Exception as e:
                print(f"[Matcher] 模糊匹配时出现错误: {e}")
        else:
            return None

        return None


    def _extract_path(self, url: str) -> str:
        """Extract path from URL for matching purposes."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.path

    def find_best_url(self, target_url: str, playback_data: Dict[str, List]) -> Optional[str]:
        """Alias for find_best_match for compatibility."""
        return self.find_best_match(target_url,playback_data)
