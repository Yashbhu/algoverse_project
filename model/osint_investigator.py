import requests 
import spacy
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import re
import google.generativeai as genai

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel("models/gemini-2.5-pro")

# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

def safe_filename(text):
    return re.sub(r'[^A-Za-z0-9_]+', '_', text)

def google_api_search(query, api_key, cse_id, max_results=100, tag=""):
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

def enrich_with_nlp(results):
    for r in results:
        text = f"{r.get('title', '')}. {r.get('snippet', '')}"
        doc = nlp(text)
        r["entities"] = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    return results

def is_name_match(target_name, entities):
    target_parts = [part.lower() for part in target_name.split() if part.strip()]
    if len(target_parts) < 2:
        # If only one name part provided, fallback to existing logic
        target = target_parts[0]
        for ent in entities:
            if ent['label'] == 'PERSON':
                person_name = ent['text'].lower()
                if target in person_name or person_name in target:
                    return True
    else:
        # Require both first and last (or all parts) to appear in entity
        for ent in entities:
            if ent['label'] == 'PERSON':
                person_name = ent['text'].lower()
                if all(part in person_name for part in target_parts):
                    return True
    return False

def gemini_summarize(name, city, extras, title, snippet, link, entities):
    # Combine extras text nicely
    extras_text = ", ".join(extras) if extras else "N/A"
    
    # Format entities list
    entity_summary = "\n".join([f'- {e["label"]}: {e["text"]}' for e in entities])
    
    # Build prompt
    prompt = f"""Search about {name}, {city}, {extras_text} on the web and integrate a summary using:
    Title: {title}
    Snippet: "{snippet}"
    Entities:
    {entity_summary}
    Link: {link}

Generate a clear, concise summary suitable for an OSINT investigation report.
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        return None




def save_json(name, city, results):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = safe_filename(name)
    safe_city = safe_filename(city)
    filename = f"osint_profile_{safe_name}_{safe_city}_{timestamp}.json"
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
    extra_text = " ".join(extra_terms)

    # === LinkedIn search ===
    linkedin_query = f'site:linkedin.com/in {name} {city} {extra_text}'
    linkedin_results = google_api_search(linkedin_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=10, tag="LinkedIn")

    # === Case/news search ===
    case_keywords = 'crime OR FIR OR arrested OR chargesheet OR court OR case site:ndtv.com OR site:thehindu.com OR site:indiatoday.in OR site:barandbench.com OR site:livelaw.in'
    news_query = f'{name} {city} {case_keywords} {extra_text}'
    case_results = google_api_search(news_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=10, tag="Case/News")

    # === General search ===
    general_query = f'{name} {city} {extra_text}'
    general_results = google_api_search(general_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=10, tag="General")

    # === Combine + NLP ===
    combined = merge_and_dedupe(linkedin_results + case_results + general_results)
    combined = enrich_with_nlp(combined)

    # === Filter ===
    filtered_results = []
    for result in combined:
         if is_name_match(name, result['entities']):
             filtered_results.append(result)
         else:
             print(f"⚠ Skipped: {result.get('title')} (no matching name)")

    for r in filtered_results:
        summary = gemini_summarize(name, city, extra_terms, r['title'], r['snippet'], r['link'], r['entities'])
        r["gemini_summary"] = summary or "Summary not available"


    save_json(name, city,filtered_results)

if __name__ == "__main__":
    main()

