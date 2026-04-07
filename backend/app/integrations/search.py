from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchEvidence:
    title: str
    url: str
    domain: str
    published_at: str
    snippet: str
    screenshot_path: str


class SearchService:
    def preview(self, destination: str, intent: str) -> dict:
        queries = [
            f"{destination} {intent} 攻略",
            f"{destination} 自驾 亲子 周末",
            f"{destination} 文旅 官方 {intent}",
        ]
        evidence = [
            SearchEvidence(
                title=f"{destination} 官方文旅指南",
                url="https://example.gov.cn/travel",
                domain="example.gov.cn",
                published_at=datetime.utcnow().strftime("%Y-%m-%d"),
                snippet=f"{destination} 的 {intent} 候选信息。",
                screenshot_path="/media/screenshots/mock-source.png",
            )
        ]
        return {
            "query_plan": queries,
            "ranking_strategy": "source_trust > recency > relevance",
            "evidence": [item.__dict__ for item in evidence],
        }


search_service = SearchService()

