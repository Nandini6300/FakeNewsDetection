
import requests
import feedparser
import re
import time

from urllib.parse import urlencode, urlparse
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}


def create_session():
    session = requests.Session()

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(HEADERS)

    return session


SESSION = create_session()


def clean_html(text):
    if not text:
        return ""

    return BeautifulSoup(
        text,
        "html.parser"
    ).get_text(" ", strip=True)


def get_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "Unknown"


def make_search_queries(query):
    original = query.strip()

    stopwords = {
        "the", "is", "was", "were", "a", "an",
        "on", "in", "at", "of", "to", "for",
        "and", "that", "this", "has", "have",
        "had", "successfully"
    }

    words = re.findall(r"[A-Za-z0-9]+", original)

    keywords = [
        word for word in words
        if word.lower() not in stopwords
    ]

    keyword_query = " ".join(keywords)

    queries = [original]

    if keyword_query and keyword_query.lower() != original.lower():
        queries.append(keyword_query)

    return queries


def parse_feed(url):
    try:
        response = SESSION.get(
            url,
            timeout=(8, 15)
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        articles = []

        for entry in feed.entries[:6]:

            link = entry.get("link", "")
            title = entry.get("title", "")

            if not link or not title:
                continue

            articles.append({
                "title": clean_html(title),
                "url": link,
                "domain": get_domain(link),
                "published": entry.get("published", ""),
                "summary": clean_html(
                    entry.get("summary", "")
                ),
                "content": ""
            })

        return articles

    except requests.RequestException as error:
        print("RSS connection error:", str(error)[:150])
        return []

    except Exception as error:
        print("RSS parsing error:", str(error)[:150])
        return []


def search_google_news(query):
    params = {
        "q": query,
        "hl": "en-IN",
        "gl": "IN",
        "ceid": "IN:en"
    }

    url = (
        "https://news.google.com/rss/search?"
        + urlencode(params)
    )

    return parse_feed(url)


def search_bing_news(query):
    params = {
        "q": query,
        "format": "rss",
        "setlang": "en-IN"
    }

    url = (
        "https://www.bing.com/news/search?"
        + urlencode(params)
    )

    return parse_feed(url)


def search_news(query, limit=3):

    print("\nSearching online news...")

    all_articles = []

    for search_query in make_search_queries(query):

        print("\nSearch query:", search_query)

        # First try Google News
        results = search_google_news(search_query)

        if results:
            print("Google News articles:", len(results))
            all_articles.extend(results)

        else:
            print("Google News unavailable. Trying Bing News...")

            # Fallback search
            results = search_bing_news(search_query)

            print("Bing News articles:", len(results))
            all_articles.extend(results)

        if len(all_articles) >= limit:
            break

        time.sleep(0.5)

    unique_articles = []
    seen_urls = set()

    for article in all_articles:

        url = article.get("url", "").split("?")[0].rstrip("/")

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        unique_articles.append(article)

    final_articles = unique_articles[:limit]

    print("\nSELECTED ARTICLES:")

    for index, article in enumerate(final_articles, start=1):
        print("\n", index)
        print("TITLE:", article["title"])
        print("DOMAIN:", article["domain"])
        print("URL:", article["url"])

    print("\nTOTAL ARTICLES:", len(final_articles))

    return final_articles
