import os
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RETENTION_DAYS = 30

# Rules
ALLOWED_CATEGORIES = ["경제", "글로벌"]
MAX_ARTICLES_PER_FEED = 8
MAX_CLUSTERS = 10
ENABLE_WEB_CRAWLING = True  # Enable web crawling for full article body extraction

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

# API Keys & Flags
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", os.environ.get("NEWSAPI_KEY", ""))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    config_file = DATA_DIR / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                GEMINI_API_KEY = cfg.get("gemini_api_key", cfg.get("GEMINI_API_KEY", ""))
        except Exception:
            pass

COLLECT_MODE = os.environ.get("COLLECT_MODE", "collect")
