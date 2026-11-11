
import requests
import trafilatura
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}


def get_domain(url):
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return "Unknown"


def extract_article(article):

    article = article.copy()
    url = article.get("url", "")

    article["content"] = ""
    article["extraction_status"] = "failed"
    article["extraction_method"] = "none"

    if not url.startswith(("http://", "https://")):
        return article

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10,
            allow_redirects=True
        )

        response.raise_for_status()

        final_url = response.url

        article["url"] = final_url
        article["domain"] = get_domain(final_url)

        content = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=False,
            favor_precision=True
        )

        if content and len(content.strip()) >= 150:

            article["content"] = content.strip()[:2000]
            article["extraction_status"] = "success"
            article["extraction_method"] = "full_article"

        else:
            summary = article.get("summary", "").strip()

            if len(summary) >= 50:
                article["content"] = summary[:1000]
                article["extraction_status"] = "partial"
                article["extraction_method"] = "search_summary"

        print(
            "EXTRACTION:",
            article.get("title", ""),
            "|",
            article["extraction_status"]
        )

        return article

    except requests.RequestException as error:

        print("Article request error:", str(error)[:150])

    except Exception as error:

        print("Article extraction error:", str(error)[:150])

    # Use a search summary only as partial information.
    summary = article.get("summary", "").strip()

    if len(summary) >= 50:
        article["content"] = summary[:1000]
        article["extraction_status"] = "partial"
        article["extraction_method"] = "search_summary"

    return article


def collect_article_content(articles):

    extracted_articles = []

    articles = articles[:3]

    with ThreadPoolExecutor(max_workers=3) as executor:

        futures = [
            executor.submit(extract_article, article)
            for article in articles
        ]

        for future in as_completed(futures):

            try:
                article = future.result()

                if article.get("content"):
                    extracted_articles.append(article)

            except Exception as error:
                print("Extraction error:", error)

    print("\nARTICLE EXTRACTION SUMMARY")

    for article in extracted_articles:
        print("TITLE:", article.get("title"))
        print("DOMAIN:", article.get("domain"))
        print("STATUS:", article.get("extraction_status"))
        print("METHOD:", article.get("extraction_method"))

    return extracted_articles
