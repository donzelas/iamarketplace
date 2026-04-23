import logging
from typing import Any

logger = logging.getLogger(__name__)


class GoogleAdsManager:
    """Google Ads API client.

    Requer: google-ads Python library + Developer Token + OAuth credentials.
    Docs: https://developers.google.com/google-ads/api/docs/start
    """

    def __init__(self, config: dict):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google.ads.googleads.client import GoogleAdsClient
                self._client = GoogleAdsClient.load_from_dict({
                    "developer_token": self.config["developer_token"],
                    "client_id": self.config["client_id"],
                    "client_secret": self.config["client_secret"],
                    "refresh_token": self.config["refresh_token"],
                    "use_proto_plus": True,
                })
            except ImportError:
                logger.error("google-ads package not installed")
                raise
        return self._client

    def get_campaign_performance(self, date_from: str, date_to: str) -> list[dict]:
        client = self._get_client()
        customer_id = self.config["customer_id"]
        service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_per_conversion
            FROM campaign
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
            ORDER BY metrics.cost_micros DESC
        """

        response = service.search(customer_id=customer_id, query=query)
        results = []
        for row in response:
            cost = row.metrics.cost_micros / 1_000_000
            results.append({
                "platform": "google_ads",
                "campaign_id": str(row.campaign.id),
                "campaign_name": row.campaign.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "spend": round(cost, 2),
                "conversions": round(row.metrics.conversions, 2),
                "revenue": round(row.metrics.conversions_value, 2),
                "cpc": round(cost / max(row.metrics.clicks, 1), 2),
                "ctr": round(row.metrics.clicks / max(row.metrics.impressions, 1) * 100, 2),
                "roas": round(row.metrics.conversions_value / max(cost, 0.01), 2),
            })
        return results

    def get_auction_insights(self, campaign_id: str) -> list[dict]:
        client = self._get_client()
        customer_id = self.config["customer_id"]
        service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                auction_insight.display_domain,
                metrics.auction_insight_search_impression_share,
                metrics.auction_insight_search_overlap_rate,
                metrics.auction_insight_search_position_above_rate,
                metrics.auction_insight_search_top_impression_percentage
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """
        response = service.search(customer_id=customer_id, query=query)
        return [
            {
                "domain": row.auction_insight.display_domain,
                "impression_share": row.metrics.auction_insight_search_impression_share,
                "overlap_rate": row.metrics.auction_insight_search_overlap_rate,
                "position_above_rate": row.metrics.auction_insight_search_position_above_rate,
            }
            for row in response
        ]

    def update_keyword_bid(self, ad_group_id: str, criterion_id: str, new_bid_micros: int) -> dict:
        client = self._get_client()
        customer_id = self.config["customer_id"]
        service = client.get_service("AdGroupCriterionService")

        operation = client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = service.ad_group_criterion_path(customer_id, ad_group_id, criterion_id)
        criterion.cpc_bid_micros = new_bid_micros
        client.copy_from(
            operation.update_mask,
            client.get_type("FieldMask")(paths=["cpc_bid_micros"]),
        )
        response = service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])
        logger.info("Google Ads bid updated: group=%s, criterion=%s, bid=%d", ad_group_id, criterion_id, new_bid_micros)
        return {"status": "updated", "resource": response.results[0].resource_name}

    def update_campaign_budget(self, campaign_budget_id: str, new_budget_micros: int) -> dict:
        client = self._get_client()
        customer_id = self.config["customer_id"]
        service = client.get_service("CampaignBudgetService")

        operation = client.get_type("CampaignBudgetOperation")
        budget = operation.update
        budget.resource_name = service.campaign_budget_path(customer_id, campaign_budget_id)
        budget.amount_micros = new_budget_micros
        client.copy_from(
            operation.update_mask,
            client.get_type("FieldMask")(paths=["amount_micros"]),
        )
        response = service.mutate_campaign_budgets(customer_id=customer_id, operations=[operation])
        logger.info("Google Ads budget updated: %s -> %d micros", campaign_budget_id, new_budget_micros)
        return {"status": "updated", "resource": response.results[0].resource_name}
