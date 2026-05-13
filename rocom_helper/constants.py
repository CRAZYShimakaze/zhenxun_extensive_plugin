from __future__ import annotations

from datetime import timedelta, timezone

DEFAULT_API_BASE_URL = "https://wegame.shallow.ink"
DEFAULT_API_KEY = "sk-ff14f964051a5c966564e29b5bd3a768"
DEFAULT_WIKI_BASE_URL = "https://rocom.game-walkthrough.com"
DEFAULT_TIMEOUT = 15
CN_TZ = timezone(timedelta(hours=8))
ROUND_START_HOURS = (8, 12, 16, 20)
WIKI_CACHE_TTL_SECONDS = 6 * 60 * 60
WEGAME_WIKI_RETRY_SECONDS = 30 * 60
IMAGE_FETCH_CONCURRENCY = 4
MERCHANT_HIGHLIGHT_ITEM_NAMES = {"国王球", "棱镜球", "炫彩精灵蛋"}
