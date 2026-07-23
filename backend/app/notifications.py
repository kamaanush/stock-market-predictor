import httpx

from .config import Settings


async def send_telegram(settings: Settings, message: str) -> bool:
    """Send only when both bot token and target chat ID are configured locally."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json={"chat_id": settings.telegram_chat_id, "text": message})
        response.raise_for_status()
    return True
