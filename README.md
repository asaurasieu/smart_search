# Smart Search

> This project was built using **vibecoding** — an AI-assisted development approach where the application is designed and implemented through natural language prompts rather than writing code manually. The architecture, logic, and UI were all generated iteratively using [Claude](https://claude.ai) by Anthropic, with the developer guiding the process through high-level intent and feedback rather than low-level implementation details.

A lightweight, free web app for AI-powered information discovery — no API keys required. Browse curated AI and global news, or deep search any topic with results scaffolded from beginner to advanced.

## Features

**News Feed** — Browse the latest articles across 7 preset categories:

- Latest AI Advancements, AI Startups, AI Models, AI Agents, AI Future
- International Relations, Counterterrorism Research

Articles are filtered to the past 2 weeks and sorted newest-first.

**Deep Search** — Enter any topic to get 10 curated results ordered by knowledge level:

- Introductory → Intermediate → Advanced
- Color-coded difficulty badges help you build understanding systematically

## Tech Stack

| Layer    | Technology                                |
| -------- | ----------------------------------------- |
| Backend  | FastAPI + Uvicorn (async Python)          |
| Search   | DuckDuckGo via `ddgs` (no API key needed) |
| Scraping | `httpx` + `BeautifulSoup4`                |
| Frontend | Vanilla JS, single HTML file, dark theme  |

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## API

| Endpoint  | Method | Body                       | Description                      |
| --------- | ------ | -------------------------- | -------------------------------- |
| `/news`   | POST   | `{ "category": "string" }` | Fetch latest news for a category |
| `/search` | POST   | `{ "prompt": "string" }`   | Deep search with tiered results  |

Both endpoints return `{ "results": [Article] }` where each article contains `title`, `url`, `snippet`, `content`, `date`, and `level`.

## How It Works

- **News Feed**: Queries DuckDuckGo for the selected category, filters to articles from the past 14 days, and returns up to 10 results sorted by date. Falls back to all results if the 14-day window is empty.
- **Deep Search**: Runs three tiered queries (introductory, intermediate, advanced) in parallel, deduplicates by URL, and returns results ordered by knowledge level.
- Article content is fetched concurrently with `asyncio.gather()` and extracted via BeautifulSoup (up to 3000 characters per article).

## Requirements

- Python 3.8+
- See `requirements.txt` for full dependency list
