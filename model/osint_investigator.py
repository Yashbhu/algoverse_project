import requests
import spacy
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")


# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

def google_api_search(query, api_key, cse_id, max_results=5, tag=""):
    url = "https://www.googleapis.com/customsearch/v1"
    results = []
    start = 1
    while len(results) < max_results:
        params = {
            "q": query,
            "key": api_key,
            "cx": cse_id,
            "num": min(10, max_results - len(results)),
            "start": start,
            "gl": "in",
            "hl": "en"
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            print(f"❌ Google API error {resp.status_code}: {resp.text}")
            break
        items = resp.json().get("items", [])
        if not items:
            break
        for item in items:
            results.append({
                "source": tag,
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet", "")
            })
        start += len(items)
    print(f"✅ {tag} search got {len(results)} results for query: {query}")
    return results

def merge_and_dedupe(results):
    seen = set()
    deduped = []
    for r in results:
        link = r.get("link")
        if link and link not in seen:
            seen.add(link)
            deduped.append(r)
    return deduped

def score_results(results, name, city, extra_terms=[]):
    name_parts = [p.lower() for p in name.split() if p.strip()]
    city = city.lower()
    extra_terms = [e.lower() for e in extra_terms]

    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
        score = 0

        # Each name part gets equal weight +1 if found
        for part in name_parts:
            if part in text:
                score += 1

        if city in text:
            score += 1

        for term in extra_terms:
            if term in text:
                score += 1

        if r["source"] == "LinkedIn" and "linkedin.com/in" in r.get("link", "").lower():
            score += 1

        r["score"] = score
    return results

def enrich_with_nlp(results):
    for r in results:
        text = f"{r.get('title', '')}. {r.get('snippet', '')}"
        doc = nlp(text)
        r["entities"] = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    return results

def filter_by_score(results, min_score=3):
    filtered = [r for r in results if r["score"] >= min_score]
    print(f"✅ Filtered: {len(filtered)} / {len(results)} results (score >= {min_score})")
    return filtered


def save_json(name, city, results):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"osint_profile_{name.replace(' ', '_')}_{city.replace(' ', '_')}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ Results saved to {filename}")

def main():
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise ValueError("Missing Google API key or CSE ID in .env")

    name = input("Enter name: ").strip()
    city = input("Enter city: ").strip()
    extra_input = input("Optional extra terms (comma-separated e.g. doctor, IIT): ").strip()
    extra_terms = [e.strip() for e in extra_input.split(",")] if extra_input else []

    # === LinkedIn search ===
    linkedin_query = f'site:linkedin.com/in "{name}" "{city}"'
    linkedin_results = google_api_search(linkedin_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=10, tag="LinkedIn")

    # === Case/news search ===
    case_keywords = 'crime OR FIR OR arrested OR chargesheet OR court OR case site:ndtv.com OR site:thehindu.com OR site:indiatoday.in OR site:barandbench.com OR site:livelaw.in'
    news_query = f'"{name}" "{city}" {case_keywords}'
    case_results = google_api_search(news_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=10, tag="Case/News")

    # === Process ===
    linkedin_results = score_results(linkedin_results, name, city, extra_terms)
    case_results = score_results(case_results, name, city, extra_terms)

    linkedin_results = enrich_with_nlp(linkedin_results)
    case_results = enrich_with_nlp(case_results)

    combined = merge_and_dedupe(linkedin_results + case_results)
    if extra_terms==[]:
        min_score = 4
    else:
        min_score=5
      # You can change this threshold as needed
    filtered = filter_by_score(combined, min_score)
    
    save_json(name, city, filtered)

if __name__ == "__main__":
    main()
