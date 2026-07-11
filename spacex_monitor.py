"""Pull SpaceX-related headlines from RSS feeds, score sentiment, and log new entries to CSV."""

import csv
import json
import os
from datetime import datetime, timezone

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_LINKS_PATH = os.path.join(BASE_DIR, "seen_links.json")
CSV_PATH = os.path.join(BASE_DIR, "spacex_news_log.csv")

CSV_COLUMNS = [
    "fetched_at_utc",
    "source",
    "published",
    "title",
    "link",
    "sentiment_score",
    "sentiment_label",
]

KEYWORDS = ["spacex", "starship", "falcon 9", "falcon heavy", "elon musk"]

# Feeds that carry general news and need keyword filtering.
MAINSTREAM_AND_NICHE_FEEDS = {
    "Reuters Tech": "https://www.reutersagency.com/feed/?best-topics=tech",
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "CNBC Tech": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
    "NPR Business": "https://feeds.npr.org/1006/rss.xml",
    "The Guardian Space": "https://www.theguardian.com/science/space/rss",
    "SpaceNews": "https://spacenews.com/feed/",
    "NASASpaceflight": "https://www.nasaspaceflight.com/feed/",
    "Space.com": "https://www.space.com/feeds/all",
    "Ars Technica Space": "https://feeds.arstechnica.com/arstechnica/space",
    "Teslarati Space": "https://www.teslarati.com/category/space/feed/",
    "Spaceflight Now": "https://spaceflightnow.com/feed/",
    "Payload Space": "https://payloadspace.com/feed/",
    "The Verge Space": "https://www.theverge.com/rss/space/index.xml",
}

# Feeds that are already scoped to SpaceX/Starship search queries; no keyword filter needed.
SEARCH_FEEDS = {
    "Google News SpaceX": "https://news.google.com/rss/search?q=SpaceX+when:1d&hl=en-US&gl=US&ceid=US:en",
    "Google News Starship": "https://news.google.com/rss/search?q=Starship+launch+when:1d&hl=en-US&gl=US&ceid=US:en",
    "Bing News SpaceX": "https://www.bing.com/news/search?q=SpaceX&format=RSS",
}


def matches_keywords(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in KEYWORDS)


def load_seen_links():
    if not os.path.exists(SEEN_LINKS_PATH):
        return set()
    with open(SEEN_LINKS_PATH, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_seen_links(seen_links):
    with open(SEEN_LINKS_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_links), f, indent=2)


def classify_sentiment(compound_score):
    if compound_score >= 0.25:
        return "positive"
    if compound_score <= -0.25:
        return "negative"
    return "neutral"


def fetch_entries():
    """Fetch and filter entries from all feeds, returning a list of (source, entry) tuples."""
    collected = []

    for source, url in MAINSTREAM_AND_NICHE_FEEDS.items():
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            if matches_keywords(f"{title} {summary}"):
                collected.append((source, entry))

    for source, url in SEARCH_FEEDS.items():
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            collected.append((source, entry))

    return collected


def main():
    analyzer = SentimentIntensityAnalyzer()
    seen_links = load_seen_links()
    entries = fetch_entries()

    new_rows = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    for source, entry in entries:
        link = entry.get("link", "")
        if not link or link in seen_links:
            continue

        title = entry.get("title", "")
        published = entry.get("published", entry.get("updated", ""))

        scores = analyzer.polarity_scores(title)
        compound = scores["compound"]
        label = classify_sentiment(compound)

        new_rows.append({
            "fetched_at_utc": fetched_at,
            "source": source,
            "published": published,
            "title": title,
            "link": link,
            "sentiment_score": compound,
            "sentiment_label": label,
        })
        seen_links.add(link)

    if new_rows:
        file_exists = os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerows(new_rows)
        save_seen_links(seen_links)
        print(f"Added {len(new_rows)} new entries to {CSV_PATH}")
    else:
        print("No new entries found.")


if __name__ == "__main__":
    main()
