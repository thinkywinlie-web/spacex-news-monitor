"""Pull SpaceX-related headlines from RSS feeds, score sentiment, and log new entries to CSV."""

import csv
import json
import os
from datetime import datetime, timezone

import feedparser
from dateutil import parser as date_parser
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


MIN_DATETIME = datetime.min.replace(tzinfo=timezone.utc)


def parse_date_string(value):
    """Best-effort parse of a date string into an aware UTC-comparable datetime."""
    if not value:
        return MIN_DATETIME
    try:
        parsed = date_parser.parse(value)
    except (ValueError, OverflowError):
        return MIN_DATETIME
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_published(entry):
    """Sort key for a feed entry, preferring feedparser's normalized struct_time."""
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time:
        try:
            return datetime(*struct_time[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return parse_date_string(entry.get("published", entry.get("updated", "")))


def load_existing_rows():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
            "_sort_key": parse_published(entry),
        })
        seen_links.add(link)

    if not new_rows:
        print("No new entries found.")
        return

    existing_rows = load_existing_rows()
    for row in existing_rows:
        row["_sort_key"] = parse_date_string(row.get("published", ""))

    all_rows = existing_rows + new_rows
    all_rows.sort(key=lambda row: row["_sort_key"], reverse=True)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    save_seen_links(seen_links)
    print(f"Added {len(new_rows)} new entries; {len(all_rows)} total, sorted newest first")


if __name__ == "__main__":
    main()
