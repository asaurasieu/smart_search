import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ddgs import DDGS
from bs4 import BeautifulSoup

app = FastAPI(title="Smart Search")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


class NewsRequest(BaseModel):
    category: str


class SearchRequest(BaseModel):
    prompt: str


class Article(BaseModel):
    title: str
    url: str
    snippet: str
    content: str
    date: str
    level: str = ""


class SearchResponse(BaseModel):
    results: list[Article]


async def fetch_article_text(url: str, max_chars: int = 3000) -> str:
    if not url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers=HEADERS) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return ""
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            paragraphs = soup.find_all("p")
            text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
            return text[:max_chars].strip()
    except Exception:
        return ""


@app.post("/news", response_model=SearchResponse)
async def news(request: NewsRequest):
    category = request.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    with DDGS() as ddgs:
        raw_results = list(ddgs.news(category, max_results=15, timelimit="m"))

    # Keep only articles from the last 14 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    filtered = []
    for r in raw_results:
        date_str = r.get("date", "")
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt >= cutoff:
                filtered.append(r)
        except Exception:
            filtered.append(r)

    # Fallback to all results if 2-week filter yields nothing
    if not filtered:
        filtered = raw_results

    filtered.sort(key=lambda r: r.get("date", ""), reverse=True)
    filtered = filtered[:10]

    if not filtered:
        raise HTTPException(status_code=404, detail="No results found")

    contents = await asyncio.gather(*[fetch_article_text(r.get("url", "")) for r in filtered])

    articles = [
        Article(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("body", ""),
            content=content,
            date=r.get("date", ""),
            level="",
        )
        for r, content in zip(filtered, contents)
    ]

    return SearchResponse(results=articles)


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Three query tiers to produce basic → advanced progression
    tiers = [
        ("introductory",  f"introduction to {prompt} beginners guide overview explained"),
        ("intermediate",  f"{prompt} how it works concepts guide"),
        ("advanced",      f"{prompt} advanced research technical deep dive"),
    ]
    # Targets: 4 introductory, 3 intermediate, 3 advanced = 10 total
    tier_limits = [4, 3, 3]

    seen_urls: set[str] = set()
    raw_articles: list[tuple[dict, str]] = []

    with DDGS() as ddgs:
        for (level_name, query), limit in zip(tiers, tier_limits):
            results = list(ddgs.text(query, max_results=8))
            count = 0
            for r in results:
                url = r.get("href", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                raw_articles.append((r, level_name))
                count += 1
                if count >= limit:
                    break

    if not raw_articles:
        raise HTTPException(status_code=404, detail="No results found")

    contents = await asyncio.gather(*[fetch_article_text(r.get("href", "")) for r, _ in raw_articles])

    articles = [
        Article(
            title=r.get("title", ""),
            url=r.get("href", ""),
            snippet=r.get("body", ""),
            content=content,
            date="",
            level=level_name,
        )
        for (r, level_name), content in zip(raw_articles, contents)
    ]

    return SearchResponse(results=articles)


app.mount("/", StaticFiles(directory="static", html=True), name="static")
