import logging

logger = logging.getLogger(__name__)


class RulesEngine:
    """Regras fixas de segurança que executam ANTES da IA.

    Essas regras garantem que limites críticos nunca sejam ultrapassados,
    independente do que a IA recomendar.
    """

    def __init__(self, config: dict):
        self.config = config

    def check(self, product, margin_data: dict, ad_performance: dict | None) -> dict | None:
        """Verifica regras de segurança. Retorna decisão ou None para delegar à IA."""
        margin = margin_data["margin_pct"]

        # EMERGÊNCIA: Margem negativa — produto dando prejuízo
        if margin < 0:
            logger.critical("EMERGENCY: Negative margin (%.1f%%) for product %s", margin, product.sku)
            return {
                "action": "ADJUST_PRICE",
                "new_price": self._emergency_price(product, margin_data),
                "reason": f"EMERGÊNCIA: Margem negativa ({margin:.1f}%). Preço precisa subir imediatamente.",
                "confidence": 1.0,
                "urgency": "critical",
                "source": "rules_engine",
            }

        # CRÍTICO: Margem abaixo do mínimo global
        global_min = float(self.config.get("global_min_margin_pct", 10))
        if margin < global_min:
            logger.warning("CRITICAL: Margin %.1f%% below global minimum %.1f%% for %s", margin, global_min, product.sku)
            return {
                "action": "ADJUST_PRICE",
                "new_price": self._min_margin_price(product, margin_data, global_min),
                "reason": f"Margem ({margin:.1f}%) abaixo do mínimo global ({global_min}%).",
                "confidence": 1.0,
                "urgency": "critical",
                "source": "rules_engine",
            }

        # CRÍTICO: Margem abaixo do mínimo do produto
        product_min = float(product.min_margin_pct)
        if margin < product_min:
            return {
                "action": "ADJUST_PRICE",
                "new_price": self._min_margin_price(product, margin_data, product_min),
                "reason": f"Margem ({margin:.1f}%) abaixo do mínimo do produto ({product_min}%).",
                "confidence": 0.95,
                "urgency": "high",
                "source": "rules_engine",
            }

        if ad_performance:
            acos = float(ad_performance.get("acos", 0))
            max_acos = float(self.config.get("max_acos", 30))

            # ACOS extremo: pausar ads
            if acos > max_acos * 1.5 and acos > 0:
                logger.warning("ACOS %.1f%% extremely high for %s, pausing ads", acos, product.sku)
                return {
                    "action": "PAUSE_AD",
                    "reason": f"ACOS ({acos:.1f}%) muito acima do máximo ({max_acos}%). Pausando ads.",
                    "confidence": 0.95,
                    "urgency": "high",
                    "source": "rules_engine",
                }

            # ACOS alto: reduzir lance
            if acos > max_acos and acos > 0:
                return {
                    "action": "REDUCE_BID",
                    "reason": f"ACOS ({acos:.1f}%) acima do máximo ({max_acos}%). Reduzindo lance.",
                    "confidence": 0.9,
                    "urgency": "medium",
                    "source": "rules_engine",
                }

        return None

    def validate_decision(self, decision: dict, product, margin_data: dict) -> dict:
        """Valida e corrige uma decisão da IA antes de executar."""
        new_price = decision.get("new_price")

        if new_price is not None:
            min_allowed = float(product.min_price)
            if new_price < min_allowed:
                decision["new_price"] = min_allowed
                decision["reason"] += f" [Corrigido: preço ajustado para mínimo R${min_allowed:.2f}]"

            max_allowed = float(product.max_price) if product.max_price else None
            if max_allowed and new_price > max_allowed:
                decision["new_price"] = max_allowed
                decision["reason"] += f" [Corrigido: preço ajustado para máximo R${max_allowed:.2f}]"

            max_change_pct = float(self.config.get("max_price_change_pct", 10))
            current = float(product.current_price)
            change_pct = abs(new_price - current) / max(current, 0.01) * 100
            if change_pct > max_change_pct and decision.get("urgency") != "critical":
                if new_price > current:
                    decision["new_price"] = round(current * (1 + max_change_pct / 100), 2)
                else:
                    decision["new_price"] = round(current * (1 - max_change_pct / 100), 2)
                decision["reason"] += f" [Corrigido: ajuste limitado a {max_change_pct}% por ciclo]"

        return decision

    @staticmethod
    def _emergency_price(product, margin_data: dict) -> float:
        total_costs = margin_data["total_costs"]
        return round(total_costs * 1.15, 2)

    @staticmethod
    def _min_margin_price(product, margin_data: dict, target_margin: float) -> float:
        total_costs = margin_data["total_costs"]
        return round(total_costs / (1 - target_margin / 100), 2)
