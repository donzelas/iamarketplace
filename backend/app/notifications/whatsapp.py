import logging

import httpx

from .notifier import BaseNotifier

logger = logging.getLogger(__name__)


class WhatsAppNotifier(BaseNotifier):
    """Envia notificações via WhatsApp Cloud API (Meta Business).

    Como configurar:
    1. Crie um app em developers.facebook.com
    2. Ative o produto WhatsApp
    3. Pegue o token de acesso e o phone_number_id
    4. Configure WHATSAPP_TOKEN e WHATSAPP_PHONE_ID no .env
    5. Registre o número de destino como teste ou use template aprovado
    """

    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, access_token: str, phone_number_id: str, recipient_number: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.recipient = recipient_number
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send(self, message: str) -> bool:
        clean_message = message.replace("*", "").replace("_", "").replace("`", "")

        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        resp = await self.client.post(
            url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": self.recipient,
                "type": "text",
                "text": {"preview_url": False, "body": clean_message},
            },
        )

        if resp.status_code == 200:
            logger.info("WhatsApp notification sent to %s", self.recipient)
            return True

        logger.error("WhatsApp send failed: %s %s", resp.status_code, resp.text)
        return False

    async def close(self):
        await self.client.aclose()
