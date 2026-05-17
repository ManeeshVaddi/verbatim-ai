import os
import httpx
from dataclasses import dataclass

FACTCHECK_API = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


@dataclass
class FactCheck:
    publisher: str
    rating: str
    url: str
    summary: str


def fetch_fact_checks(query: str, speaker: str | None = None) -> list[FactCheck]:
    api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY")
    search_query = f"{query} {speaker}" if speaker else query

    params: dict = {"query": search_query, "pageSize": 3}
    if api_key:
        params["key"] = api_key

    try:
        response = httpx.get(FACTCHECK_API, params=params, timeout=5.0)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    results = []
    for claim in data.get("claims", []):
        for review in claim.get("claimReview", []):
            results.append(
                FactCheck(
                    publisher=review.get("publisher", {}).get("name", "Unknown"),
                    rating=review.get("textualRating", "Unrated"),
                    url=review.get("url", ""),
                    summary=claim.get("text", ""),
                )
            )
    return results[:3]
