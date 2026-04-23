import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, message: str) -> bool:
        ...


class Notifier:
    """Envia notificações por todos os canais configurados."""

    def __init__(self):
        self.channels: list[BaseNotifier] = []

    def add_channel(self, channel: BaseNotifier):
        self.channels.append(channel)

    async def notify(self, message: str):
        for channel in self.channels:
            try:
                await channel.send(message)
            except Exception as e:
                logger.error("Notification error on %s: %s", type(channel).__name__, e)

    async def notify_decision(self, decision: dict, product_name: str):
        urgency_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(decision.get("urgency", ""), "⚪")

        msg = (
            f"{urgency_emoji} *Decisão da IA*\n\n"
            f"📦 *Produto:* {product_name}\n"
            f"⚡ *Ação:* {decision['action']}\n"
        )

        if decision.get("new_price"):
            msg += f"💰 *Novo Preço:* R$ {decision['new_price']:.2f}\n"
        if decision.get("new_bid"):
            msg += f"🎯 *Novo Lance:* R$ {decision['new_bid']:.2f}\n"

        msg += (
            f"📝 *Motivo:* {decision.get('reason', 'N/A')}\n"
            f"🎲 *Confiança:* {(decision.get('confidence', 0) * 100):.0f}%\n"
            f"🚨 *Urgência:* {decision.get('urgency', 'N/A')}\n"
        )

        if decision.get("source") == "rules_engine":
            msg += "\n⚠️ _Decisão automática (regra de segurança)_"
        else:
            msg += "\n🤖 _Aguardando aprovação no dashboard_"

        await self.notify(msg)

    async def notify_margin_alert(self, product_name: str, margin_pct: float, health: str):
        emoji = {"HEALTHY": "✅", "WARNING": "⚠️", "CRITICAL": "🔴", "EMERGENCY": "🚨"}.get(health, "❓")

        msg = (
            f"{emoji} *Alerta de Margem*\n\n"
            f"📦 *Produto:* {product_name}\n"
            f"📊 *Margem:* {margin_pct:.1f}%\n"
            f"🏥 *Status:* {health}\n"
        )

        await self.notify(msg)
