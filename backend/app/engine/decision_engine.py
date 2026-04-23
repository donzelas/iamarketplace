import json
import logging

from openai import AsyncOpenAI

from .prompts import SYSTEM_PROMPT, build_analysis_prompt
from .rules import RulesEngine

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Motor de decisão com 3 camadas: Regras -> IA -> Validação."""

    def __init__(self, llm_client: AsyncOpenAI, rules: RulesEngine, config: dict):
        self.llm = llm_client
        self.rules = rules
        self.config = config

    async def evaluate(
        self,
        product,
        market_analysis: dict,
        margin_data: dict,
        ad_performance: dict | None = None,
    ) -> dict:
        # CAMADA 1: Regras fixas de segurança
        rule_decision = self.rules.check(product, margin_data, ad_performance)
        if rule_decision:
            logger.info("Rules engine triggered for %s: %s", product.sku, rule_decision["action"])
            return rule_decision

        # CAMADA 2: Análise do LLM
        prompt = build_analysis_prompt(product, market_analysis, margin_data, ad_performance, self.config)

        try:
            response = await self.llm.chat.completions.create(
                model=self.config.get("llm_model", "gpt-4o"),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500,
            )

            raw = response.choices[0].message.content
            decision = json.loads(raw)
            decision["source"] = "llm"

        except json.JSONDecodeError as e:
            logger.error("LLM returned invalid JSON: %s", e)
            return {
                "action": "HOLD",
                "reason": "Erro ao processar resposta da IA. Mantendo posição atual.",
                "confidence": 0.0,
                "urgency": "low",
                "source": "error",
            }
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return {
                "action": "HOLD",
                "reason": f"Erro na chamada da IA: {str(e)[:100]}. Mantendo posição atual.",
                "confidence": 0.0,
                "urgency": "low",
                "source": "error",
            }

        # CAMADA 3: Validação de segurança
        decision = self.rules.validate_decision(decision, product, margin_data)

        logger.info(
            "AI decision for %s: %s (confidence=%.2f, urgency=%s)",
            product.sku, decision["action"], decision.get("confidence", 0), decision.get("urgency", "?"),
        )
        return decision
