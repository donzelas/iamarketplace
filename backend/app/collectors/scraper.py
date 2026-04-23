import logging
import re
from datetime import datetime

from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)


class MarketplaceScraper:
    """Scraper genérico para coletar dados de concorrentes quando a API não é suficiente."""

    SEARCH_URLS = {
        "mercadolivre": "https://lista.mercadolivre.com.br/{keyword}",
        "shopee": "https://shopee.com.br/search?keyword={keyword}",
        "amazon": "https://www.amazon.com.br/s?k={keyword}",
        "magalu": "https://www.magazineluiza.com.br/busca/{keyword}",
    }

    async def scrape_search_results(self, marketplace: str, keyword: str, limit: int = 20) -> list[dict]:
        url_template = self.SEARCH_URLS.get(marketplace)
        if not url_template:
            logger.warning("No scraper URL for marketplace: %s", marketplace)
            return []

        formatted_keyword = keyword.replace(" ", "-" if marketplace == "mercadolivre" else "+")
        url = url_template.format(keyword=formatted_keyword)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)

                parser = self._get_parser(marketplace)
                results = await parser(page, limit)

                await browser.close()
                return results

        except Exception as e:
            logger.error("Scraper error for %s '%s': %s", marketplace, keyword, e)
            return []

    def _get_parser(self, marketplace: str):
        parsers = {
            "mercadolivre": self._parse_ml,
            "shopee": self._parse_shopee,
            "amazon": self._parse_amazon,
            "magalu": self._parse_magalu,
        }
        return parsers.get(marketplace, self._parse_generic)

    async def _parse_ml(self, page: Page, limit: int) -> list[dict]:
        items = await page.query_selector_all(".ui-search-layout__item")
        results = []
        for idx, item in enumerate(items[:limit]):
            try:
                title_el = await item.query_selector(".ui-search-item__title")
                price_int = await item.query_selector(".andes-money-amount__fraction")
                price_cents = await item.query_selector(".andes-money-amount__cents")
                link_el = await item.query_selector("a.ui-search-link")
                shipping_el = await item.query_selector(".ui-search-item__shipping")

                title = await title_el.inner_text() if title_el else ""
                price_str = await price_int.inner_text() if price_int else "0"
                cents_str = await price_cents.inner_text() if price_cents else "00"
                price = self._parse_price(f"{price_str},{cents_str}")
                url = await link_el.get_attribute("href") if link_el else ""
                free_ship = shipping_el is not None

                results.append({
                    "marketplace": "mercadolivre",
                    "title": title,
                    "price": price,
                    "free_shipping": free_ship,
                    "url": url,
                    "position": idx + 1,
                    "collected_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.debug("ML parse item error: %s", e)
        return results

    async def _parse_shopee(self, page: Page, limit: int) -> list[dict]:
        await page.wait_for_timeout(3000)
        items = await page.query_selector_all(".shopee-search-item-result__item")
        results = []
        for idx, item in enumerate(items[:limit]):
            try:
                title_el = await item.query_selector("div[data-sqe='name']")
                price_el = await item.query_selector(".nt5f2I")

                title = await title_el.inner_text() if title_el else ""
                price_text = await price_el.inner_text() if price_el else "0"
                price = self._parse_price(price_text)

                results.append({
                    "marketplace": "shopee",
                    "title": title,
                    "price": price,
                    "free_shipping": False,
                    "position": idx + 1,
                    "collected_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.debug("Shopee parse item error: %s", e)
        return results

    async def _parse_amazon(self, page: Page, limit: int) -> list[dict]:
        items = await page.query_selector_all("[data-component-type='s-search-result']")
        results = []
        for idx, item in enumerate(items[:limit]):
            try:
                title_el = await item.query_selector("h2 a span")
                price_whole = await item.query_selector(".a-price-whole")
                price_frac = await item.query_selector(".a-price-fraction")
                link_el = await item.query_selector("h2 a")

                title = await title_el.inner_text() if title_el else ""
                whole = await price_whole.inner_text() if price_whole else "0"
                frac = await price_frac.inner_text() if price_frac else "00"
                price = self._parse_price(f"{whole},{frac}")
                href = await link_el.get_attribute("href") if link_el else ""
                url = f"https://www.amazon.com.br{href}" if href and not href.startswith("http") else href

                results.append({
                    "marketplace": "amazon",
                    "title": title,
                    "price": price,
                    "url": url,
                    "free_shipping": False,
                    "position": idx + 1,
                    "collected_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.debug("Amazon parse item error: %s", e)
        return results

    async def _parse_magalu(self, page: Page, limit: int) -> list[dict]:
        items = await page.query_selector_all("[data-testid='product-card']")
        results = []
        for idx, item in enumerate(items[:limit]):
            try:
                title_el = await item.query_selector("h2")
                price_el = await item.query_selector("[data-testid='price-value']")

                title = await title_el.inner_text() if title_el else ""
                price_text = await price_el.inner_text() if price_el else "0"
                price = self._parse_price(price_text)

                results.append({
                    "marketplace": "magalu",
                    "title": title,
                    "price": price,
                    "free_shipping": False,
                    "position": idx + 1,
                    "collected_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.debug("Magalu parse item error: %s", e)
        return results

    async def _parse_generic(self, page: Page, limit: int) -> list[dict]:
        return []

    @staticmethod
    def _parse_price(text: str) -> float:
        cleaned = re.sub(r"[^\d,.]", "", text)
        cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
