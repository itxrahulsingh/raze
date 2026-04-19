"""
Free web search integration using DuckDuckGo API
No API key required - completely free and open source
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class WebSearchEngine:
    """
    Free web search using DuckDuckGo (instant answer API).
    No authentication required.
    """

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout
        self.base_url = "https://api.duckduckgo.com"

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search the web using DuckDuckGo.

        Parameters
        ----------
        query       : The search query
        max_results : Maximum number of results to return

        Returns
        -------
        List of search results with title, URL, and snippet
        """
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        params = {
                            "q": query,
                            "format": "json",
                            "no_redirect": 1,
                            "no_html": 1,
                            "skip_disambig": 1,
                        }

                        resp = await client.get(self.base_url, params=params)
                        resp.raise_for_status()
                        data = resp.json()

                        # Parse results
                        results = []

                        # Add instant answer if available
                        if data.get("Answer"):
                            results.append({
                                "title": "Direct Answer",
                                "url": data.get("AbstractURL", ""),
                                "snippet": data.get("Answer", ""),
                                "source": "instant_answer",
                            })

                        # Add related topics
                        for item in data.get("RelatedTopics", [])[:max_results]:
                            if "FirstURL" in item:
                                results.append({
                                    "title": item.get("Text", "")[:100],
                                    "url": item.get("FirstURL", ""),
                                    "snippet": item.get("Text", "")[:200],
                                    "source": "related_topic",
                                })

                        logger.info(
                            "web_search_completed",
                            query=query,
                            results_count=len(results),
                        )
                        return results[:max_results]

        except Exception as e:
            logger.warning("web_search_failed", query=query, error=str(e))
            return []

    async def search_with_summary(
        self,
        query: str,
        max_results: int = 3,
    ) -> str:
        """
        Search and return a formatted summary for chat context.

        Parameters
        ----------
        query       : The search query
        max_results : Maximum number of results

        Returns
        -------
        Formatted string with search results
        """
        results = await self.search(query, max_results)

        if not results:
            return f"No search results found for '{query}'"

        summary = f"Web search results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            summary += f"{i}. {result['title']}\n"
            summary += f"   URL: {result['url']}\n"
            summary += f"   {result['snippet']}\n\n"

        return summary.strip()


# Singleton instance
_web_search_engine: WebSearchEngine | None = None


def get_web_search_engine() -> WebSearchEngine:
    """Get or create the web search engine singleton."""
    global _web_search_engine
    if _web_search_engine is None:
        _web_search_engine = WebSearchEngine()
    return _web_search_engine
