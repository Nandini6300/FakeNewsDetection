
from flask import Flask, render_template, request, jsonify
import time

from news_search import search_news
from article_extractor import collect_article_content
from ai_verifier import verify_news


app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/check", methods=["POST"])
def check_news():

    total_start = time.time()

    try:

        data = request.get_json(silent=True) or {}

        news = data.get("news", "").strip()

        if not news:
            return jsonify({
                "error": "Please enter some news."
            }), 400

        if len(news) > 3000:
            return jsonify({
                "error": "News must not exceed 3000 characters."
            }), 400

        print("\n" + "=" * 50)
        print("STARTING TRUTHSCAN AI")
        print("=" * 50)

        # STEP 1: Search online

        print("\n[1] Searching online...")

        search_start = time.time()

        articles = search_news(news, limit=3)

        search_time = time.time() - search_start

        print("Articles found:", len(articles))
        print("Search time:", round(search_time, 2), "seconds")

        if not articles:
            return jsonify({
                "error": (
                    "No relevant online articles were found. "
                    "Please try a clearer or more specific news claim."
                )
            }), 503

        # STEP 2: Extract article content

        print("\n[2] Extracting article content...")

        extraction_start = time.time()

        articles = collect_article_content(articles)

        extraction_time = time.time() - extraction_start

        print("\nEXTRACTED ARTICLES:")

        for article in articles:

            print("\nTITLE:", article.get("title"))
            print("DOMAIN:", article.get("domain"))
            print("STATUS:", article.get("extraction_status"))
            print("CONTENT:", article.get("content", "")[:400])

        print("\nArticles with content:", len(articles))
        print(
            "Extraction time:",
            round(extraction_time, 2),
            "seconds"
        )

        if not articles:
            return jsonify({
                "error": (
                    "The search results were found, but article content "
                    "could not be extracted. Please try again."
                )
            }), 503

        # STEP 3: AI verification

        print("\n[3] Starting AI verification...")

        ai_start = time.time()

        result = verify_news(news, articles)

        ai_time = time.time() - ai_start

        # STEP 4: Processing information

        total_time = time.time() - total_start

        result["input_news"] = news
        result["articles_found"] = len(articles)

        result["processing_time"] = round(total_time, 2)
        result["search_time"] = round(search_time, 2)
        result["extraction_time"] = round(extraction_time, 2)
        result["ai_time"] = round(ai_time, 2)

        print("\n" + "=" * 50)
        print("FINAL PREDICTION:", result["prediction"])
        print("CONFIDENCE:", result.get("confidence", "LOW"))
        print("TOTAL TIME:", round(total_time, 2), "seconds")
        print("=" * 50)

        return jsonify(result)

    except RuntimeError as error:

        print("\nVERIFICATION ERROR:", str(error))

        return jsonify({
            "error": str(error)
        }), 503

    except Exception as error:

        print("\nAPPLICATION ERROR:", repr(error))

        return jsonify({
            "error": (
                "Something went wrong while checking the news. "
                "Please check the terminal for details."
            )
        }), 500


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        threaded=True
    )
