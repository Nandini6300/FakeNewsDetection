
import os
import json
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"


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

        result, _ = json.JSONDecoder().raw_decode(text[start:])
        return result


def check_known_facts(news):
    text = news.lower().strip()

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
                "on 15 August 1947, not in 1950. On 26 January "
                "1950, India became a Republic. The claim confuses "
                "Independence Day with Republic Day."
            ),
            "supporting_evidence": [],
            "contradicting_evidence": [
                {
                    "source_id": "OFFICIAL1",
                    "reason": (
                        "India became independent on 15 August 1947."
                    )
                },
                {
                    "source_id": "OFFICIAL2",
                    "reason": (
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

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to your environment variables."
        )

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

        evidence += f"""
SOURCE ID: {source_id}
TITLE: {article.get('title', '')}
PUBLISHER: {article.get('publisher', '')}
DOMAIN: {article.get('domain', '')}
DATE: {article.get('published', '')}
ARTICLE CONTENT:
{content[:1800]}

------------------------------------
"""

    prompt = f"""
You are a careful news fact-checking assistant.

Compare the user's exact claim with the supplied online articles.

USER CLAIM:
{news}

ONLINE ARTICLES:
{evidence}

RULES:
1. Identify the exact central claim.
2. Check names, dates, places, numbers and events carefully.
3. Read the supplied article content before deciding.
4. Do not assume a similar headline proves the claim.
5. Do not invent sources, quotations or facts.
6. Use the supplied articles as your evidence.
7. REAL means the central claim is supported by the articles.
8. FAKE means reliable information in the articles contradicts
   the central claim.
9. If the evidence is weak or unclear, choose the best-supported
   label but set confidence to LOW and explain the uncertainty.
10. Never claim that a source supports something it does not say.
11. Cite only the source IDs supplied above.

Return ONLY valid JSON in this exact structure:

{{
  "prediction": "REAL",
  "confidence": "MEDIUM",
  "explanation": "Explain the result in simple language.",
  "supporting_evidence": [
    {{
      "source_id": "S1",
      "reason": "Explain the relevant supporting information."
    }}
  ],
  "contradicting_evidence": []
}}

prediction must be exactly REAL or FAKE.
confidence must be HIGH, MEDIUM or LOW.
Use empty arrays when no relevant evidence is available.
Do not include Markdown outside the JSON.
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=1200
            )
        )

        ai_text = response.text or ""

        print("\nRAW GEMINI RESPONSE:\n", ai_text)

        ai_result = parse_ai_json(ai_text)

        prediction = str(
            ai_result.get("prediction", "")
        ).upper().strip()

        if prediction not in ["REAL", "FAKE"]:
            raise ValueError(
                "Gemini did not return a valid REAL or FAKE prediction."
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
                    "reason": str(item.get("reason", ""))[:500]
                })
                used_source_ids.add(source_id)

        for item in ai_result.get("contradicting_evidence", []):
            if not isinstance(item, dict):
                continue

            source_id = item.get("source_id")

            if source_id in source_map:
                contradicting.append({
                    "source_id": source_id,
                    "reason": str(item.get("reason", ""))[:500]
                })
                used_source_ids.add(source_id)

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

    except Exception as error:
        print("Gemini verification error:", repr(error))
        raise RuntimeError(
            "Gemini AI verification failed: " + str(error)
        )
