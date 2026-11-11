
import requests
import json
import re


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"


def parse_ai_json(text):

    text = text.strip()

    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")

        if start == -1:
            raise ValueError("No JSON object found.")

        result, _ = json.JSONDecoder().raw_decode(
            text[start:]
        )

        return result

import re


def check_known_facts(news):

    text = news.lower().strip()

    # India became independent in 1947, not 1950.
    independence_pattern = (
        r"\bindia\b.*\b"
        r"(?:became independent|got independence|"
        r"gained independence|achieved independence|"
        r"was independent)\b"
    )

    if (
        re.search(independence_pattern, text)
        and re.search(r"\b1950\b", text)
    ):
        return {
            "prediction": "FAKE",
            "confidence": "HIGH",
            "explanation": (
                "This claim is false. India became independent "
                "from British rule on 15 August 1947, not in 1950. "
                "On 26 January 1950, the Constitution came into "
                "force and India became a Republic. The claim "
                "confuses Independence Day with Republic Day."
            ),
            "supporting_evidence": [],
            "contradicting_evidence": [
                {
                    "source_id": "OFFICIAL1",
                    "reason": (
                        "The Government of India confirms that "
                        "India became independent on 15 August 1947."
                    )
                },
                {
                    "source_id": "OFFICIAL2",
                    "reason": (
                        "The Government of India confirms that "
                        "India became a Republic on 26 January 1950."
                    )
                }
            ],
            "sources": [
                {
                    "title": "Independence Day of India",
                    "domain": "india.gov.in",
                    "url": (
                        "https://www.india.gov.in/explore-india/"
                        "facts-of-india/independence-day"
                    ),
                    "published": ""
                },
                {
                    "title": "Republic Day of India",
                    "domain": "india.gov.in",
                    "url": (
                        "https://www.india.gov.in/explore-india/"
                        "facts-of-india/republic-day"
                    ),
                    "published": ""
                }
            ]
        }

    return None


def verify_news(news, articles):
    known_result = check_known_facts(news)

    if known_result is not None:
        print("\nKNOWN FACT MATCH:", known_result["prediction"])
        return known_result
    

    if not articles:
        raise RuntimeError(
            "No online articles were found. Try another search."
        )

    source_map = {}
    evidence = ""

    for index, article in enumerate(articles[:3], start=1):

        source_id = f"S{index}"

        source_map[source_id] = article

        content = (
            article.get("content", "")
            or article.get("summary", "")
        )

        status = article.get(
            "extraction_status", "unknown"
        )

        evidence += f"""
SOURCE ID: {source_id}

TITLE: {article.get('title', '')}

PUBLISHER: {article.get('publisher', '')}

DOMAIN: {article.get('domain', '')}

DATE: {article.get('published', '')}

CONTENT STATUS: {status}

ARTICLE CONTENT:
{content[:1800]}

------------------------------------
"""

    prompt = f"""
You are a careful news fact-checking assistant.

Your job is to compare the user's exact claim with the supplied
online article evidence.

USER CLAIM:
{news}

ONLINE ARTICLES:
{evidence}

STRICT RULES:

1. Identify the exact central claim.
2. Check names, dates, places, numbers and events carefully.
3. Do not confuse two different events.
4. Do not assume an article supports a claim just because its
   headline contains similar words.
5. Read the article content before deciding.
6. A search result summary is weaker evidence than full article text.
7. Do not invent official announcements, quotations, sources or facts.
8. Do not use your own memory as proof.
9. Do not treat the absence of search results as proof that a claim is fake.
10. REAL means the central claim is supported by the supplied articles.
11. FAKE means the central claim is contradicted by reliable information
    in the supplied articles.
12. If the evidence is not clear, explain that the result is a
    low-confidence best-effort classification. Do not invent evidence.
13. Cite only source IDs that actually appear above.
14. Never claim a source confirms something unless its supplied
    content actually supports that statement.

Choose the best-supported label:
REAL or FAKE.

Return ONLY valid JSON using exactly this structure:

{{
  "prediction": "REAL",
  "confidence": "MEDIUM",
  "explanation": "A clear explanation in simple language.",
  "supporting_evidence": [
    {{
      "source_id": "S1",
      "reason": "Explain the exact information that supports the claim."
    }}
  ],
  "contradicting_evidence": []
}}

The prediction must be exactly REAL or FAKE.
Confidence must be HIGH, MEDIUM or LOW.
Use empty arrays if no relevant source supports that side.
Do not include Markdown outside the JSON.
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_predict": 400,
            "num_ctx": 4096
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=150
        )

        response.raise_for_status()

        ai_text = response.json().get("response", "")

        print("\nRAW AI RESPONSE:\n", ai_text)

        ai_result = parse_ai_json(ai_text)

        prediction = str(
            ai_result.get("prediction", "")
        ).upper().strip()

        if prediction not in ["REAL", "FAKE"]:
            raise ValueError(
                "AI did not return a valid REAL or FAKE prediction."
            )

        confidence = str(
            ai_result.get("confidence", "LOW")
        ).upper().strip()

        if confidence not in ["HIGH", "MEDIUM", "LOW"]:
            confidence = "LOW"

        explanation = ai_result.get(
            "explanation",
            "The AI could not generate an explanation."
        )

        if not isinstance(explanation, str):
            explanation = "The AI returned an invalid explanation."

        supporting = []
        contradicting = []
        used_source_ids = set()

        for item in ai_result.get("supporting_evidence", []):

            if not isinstance(item, dict):
                continue

            source_id = item.get("source_id")

            if source_id in source_map:

                supporting.append({
                    "source_id": source_id,
                    "reason": str(
                        item.get("reason", "")
                    )[:500]
                })

                used_source_ids.add(source_id)

        for item in ai_result.get("contradicting_evidence", []):

            if not isinstance(item, dict):
                continue

            source_id = item.get("source_id")

            if source_id in source_map:

                contradicting.append({
                    "source_id": source_id,
                    "reason": str(
                        item.get("reason", "")
                    )[:500]
                })

                used_source_ids.add(source_id)

        # Do not pretend that an unsupported prediction is verified.
        if prediction == "REAL" and not supporting:
            confidence = "LOW"
            explanation += (
                " The retrieved articles did not provide a clearly "
                "identified supporting source."
            )

        if prediction == "FAKE" and not contradicting:
            confidence = "LOW"
            explanation += (
                " The retrieved articles did not provide a clearly "
                "identified contradicting source."
            )

        # Return only actual URLs obtained by the search process.
        sources = []

        for source_id in sorted(
            used_source_ids,
            key=lambda value: int(value[1:])
        ):

            article = source_map[source_id]
            url = article.get("url", "")

            if not url.startswith(("http://", "https://")):
                continue

            sources.append({
                "title": article.get("title", "News article"),
                "domain": article.get("domain", "Unknown"),
                "url": url,
                "published": article.get("published", "")
            })

        return {
            "prediction": prediction,
            "confidence": confidence,
            "explanation": explanation[:2000],
            "supporting_evidence": supporting,
            "contradicting_evidence": contradicting,
            "sources": sources
        }

    except requests.RequestException as error:

        print("Ollama connection error:", error)

        raise RuntimeError(
            "Cannot connect to Ollama. Check that Ollama is running."
        )

    except Exception as error:

        print("AI verification error:", repr(error))

        raise RuntimeError(
            "AI verification failed: " + str(error)
        )
