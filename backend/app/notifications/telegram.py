import logging

import httpx

from .notifier import BaseNotifier

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Envia notificações via Telegram Bot API.

    Como configurar:
    1. Fale com @BotFather no Telegram e crie um bot
    2. Copie o token do bot
    3. Inicie conversa com o bot e envie /start
    4. Acesse https://api.telegram.org/bot<TOKEN>/getUpdates para pegar o chat_id
    5. Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env
    """

    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send(self, message: str) -> bool:
        url = f"{self.BASE_URL}/bot{self.bot_token}/sendMessage"
        resp = await self.client.post(url, json={
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })

        if resp.status_code == 200:
            logger.info("Telegram notification sent to chat %s", self.chat_id)
            return True

        logger.error("Telegram send failed: %s %s", resp.status_code, resp.text)
        return False

    async def close(self):
        await self.client.aclose()
