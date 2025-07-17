import os
import json
from datetime import datetime
import time
import re
import requests
import spacy
from dotenv import load_dotenv
import google.generativeai as genai
from collections import Counter
from rapidfuzz import fuzz
from dateutil.parser import parse as parse_date

# --- Service Configuration & Initialization ---

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

progress_store = {}

try:
    if not all([GOOGLE_API_KEY, GOOGLE_CSE_ID, GEMINI_API_KEY]):
        raise ValueError("Required API keys (GOOGLE, GEMINI) are missing from .env file.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("✅ Gemini AI model configured successfully.")

    nlp = spacy.load("en_core_web_sm")
    print("✅ spaCy NLP model loaded successfully.")

except (ValueError, OSError) as e:
    print(f"🚨 FATAL INITIALIZATION ERROR: {e}")
    model = None
    nlp = None


# --- OSINT Service Functions ---

def google_api_search(query, api_key, cse_id, max_results=10, tag=""):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"q": query, "key": api_key, "cx": cse_id, "num": max_results, "gl": "in", "hl": "en"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        results = [{
            "source": tag,
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet", ""),
            "pagemap": item.get("pagemap", {}) 
        } for item in items]
        print(f"✅ {tag} search got {len(results)} results for query: '{query}'")
        return results
    except requests.exceptions.RequestException as e:
        print(f"❌ Google API error for query '{query}': {e}")
        return []

def extract_event_from_result(result):
    try:
        metatags = result.get("pagemap", {}).get("metatags", [{}])[0]
        if 'article:published_time' in metatags:
            return parse_date(metatags['article:published_time'])
        if 'pagemap' in result and 'newsarticle' in result['pagemap'] and result['pagemap']['newsarticle'][0].get('datepublished'):
             return parse_date(result['pagemap']['newsarticle'][0]['datepublished'])
        text_to_scan = f"{result.get('title', '')} {result.get('snippet', '')}"
        dt = parse_date(text_to_scan, fuzzy_with_tokens=True)
        return dt[0]
    except (ValueError, TypeError, KeyError):
        return None

def gemini_summarize_and_analyze(name, city, all_snippets):
    if not model:
        return {
            "short_summary": "AI summarization is disabled.", 
            "detailed_summary": "Detailed analysis could not be performed as the AI model is offline.",
            "riskAnalysis": {"riskScore": 0, "riskJustification": "N/A", "sentimentScore": 0, "sentimentJustification": "N/A"}
        }

    context_block = "\n---\n".join(all_snippets)
    prompt = f"""
    As an expert OSINT analyst, analyze the following collected data snippets for an individual named '{name}' possibly related to '{city}'. This is the only information you are allowed to use.

    **Collected Data:**
    ---
    {context_block}
    ---

    **Your Tasks:**
    1.  **Generate a 'short_summary'**: A concise, 2-sentence executive summary based *only* on the provided data.
    2.  **Generate a 'detailed_summary'**: A comprehensive, multi-sentence paragraph detailing the key findings, connections, and potential implications from the data, *only* using the provided text.
    3.  **Provide a 'riskScore'**: An integer from 1 (low risk) to 10 (high risk).
    4.  **Provide a 'riskJustification'**: A single sentence explaining the risk score.
    5.  **Provide a 'sentimentScore'**: A float from -1.0 (very negative) to 1.0 (very positive).
    6.  **Provide a 'sentimentJustification'**: A single sentence explaining the sentiment score.

    **Output your response in a single, valid JSON object with the exact keys: "short_summary", "detailed_summary", "riskScore", "riskJustification", "sentimentScore", "sentimentJustification". Do not add any extra text or formatting.**
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        cleaned_text = response.text.strip()
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = cleaned_text[json_start:json_end]
            analysis = json.loads(json_str)
        else:
            raise ValueError("No valid JSON object found in the AI response.")

        return {
            "short_summary": analysis.get("short_summary", "Brief summary could not be generated."),
            "detailed_summary": analysis.get("detailed_summary", "Detailed summary could not be generated."),
            "riskAnalysis": {
                "riskScore": analysis.get("riskScore", 0),
                "riskJustification": analysis.get("riskJustification", "N/A"),
                "sentimentScore": analysis.get("sentimentScore", 0),
                "sentimentJustification": analysis.get("sentimentJustification", "N/A")
            }
        }
    except Exception as e:
        print(f"❌ Gemini AI analysis error: {e}")
        if 'response' in locals(): print(f"RAW AI RESPONSE: {response.text}")
        return {
            "short_summary": "An error occurred during AI analysis.", 
            "detailed_summary": "The detailed analysis could not be generated due to an AI error.",
            "riskAnalysis": {"riskScore": 0, "riskJustification": "Analysis failed.", "sentimentScore": 0, "sentimentJustification": "Analysis failed."}
        }

def enrich_with_nlp(results):
    if not nlp:
        for r in results: r["entities"] = []
        return results
    for r in results:
        text = f"{r.get('title', '')}. {r.get('snippet', '')}"
        doc = nlp(text)
        r["entities"] = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    return results

def is_name_match(target_name, entities):
    target_parts = {part.lower() for part in target_name.split() if part.strip()}
    for ent in entities:
        if ent['label'] == 'PERSON':
            person_name_parts = {part.lower() for part in ent['text'].split() if part.strip()}
            if target_parts.issubset(person_name_parts):
                return True
    return False

def merge_and_dedupe(results_list):
    seen_links = set()
    deduped = []
    for result in results_list:
        link = result.get("link")
        if link and link not in seen_links:
            seen_links.add(link)
            deduped.append(result)
    return deduped

def run_osint_with_progress(name, city, extras, search_id):
    global progress_store

    def update_progress(percentage, stage):
        if search_id in progress_store:
            progress_store[search_id].update({"percentage": percentage, "stage": stage})
            time.sleep(0.1)

    if not model or not nlp:
        raise ConnectionError("Backend services (AI or NLP) failed to initialize.")

    update_progress(10, "Searching Professional Profiles (LinkedIn)...")
    linkedin_results = google_api_search(f'site:linkedin.com/in "{name}" "{city}"', GOOGLE_API_KEY, GOOGLE_CSE_ID, 5, "LinkedIn")
    time.sleep(2) 

    update_progress(20, "Searching News & Legal Sources...")
    case_results = google_api_search(f'"{name}" "{city}" crime OR FIR OR arrested OR court OR case OR lawsuit', GOOGLE_API_KEY, GOOGLE_CSE_ID, 10, "Case/News")
    time.sleep(2)

    update_progress(30, "Searching Reddit Discussions...")
    reddit_results = google_api_search(f'site:reddit.com "{name}" "{city}"', GOOGLE_API_KEY, GOOGLE_CSE_ID, 5, "Reddit")
    time.sleep(2)

    update_progress(40, "Searching Wikipedia...")
    wiki_results = google_api_search(f'site:en.wikipedia.org "{name}"', GOOGLE_API_KEY, GOOGLE_CSE_ID, 2, "Wikipedia")
    time.sleep(2)

    update_progress(50, "Searching Business & Corporate Databases...")
    business_results = google_api_search(f'"{name}" site:crunchbase.com OR site:zaubacorp.com', GOOGLE_API_KEY, GOOGLE_CSE_ID, 5, "Business")
    time.sleep(2)
    
    update_progress(60, "Searching Academic Papers...")
    academic_results = google_api_search(f'"{name}" site:scholar.google.com', GOOGLE_API_KEY, GOOGLE_CSE_ID, 3, "Academic")

    update_progress(70, "Processing all sources...")
    all_results = [
        linkedin_results, case_results, reddit_results, 
        wiki_results, business_results, academic_results
    ]
    combined = merge_and_dedupe([item for sublist in all_results for item in sublist])
    if not combined:
        raise ValueError("No search results found for the query.")

    update_progress(75, "Analyzing content with NLP...")
    combined = enrich_with_nlp(combined)

    # --- REVERTED: Using the original, stricter filtering logic ---
    filtered_results = []
    for r in combined:
        if is_name_match(name, r["entities"]):
            filtered_results.append(r)
        else:
            # This helps in debugging by showing what was skipped
            print(f"⚠️ Skipped irrelevant result: {r.get('title')}")
        
    if not filtered_results:
        raise ValueError("No relevant information found matching the person after strict filtering.")


    update_progress(85, "Performing AI risk & sentiment analysis...")
    all_snippets = [f"Source: {r['source']}\nTitle: {r['title']}\nSnippet: {r['snippet']}" for r in filtered_results]
    ai_analysis = gemini_summarize_and_analyze(name, city, all_snippets)

    update_progress(95, "Constructing event timeline...")
    timeline_events = []
    for result in filtered_results:
        event_date = extract_event_from_result(result)
        if event_date:
            timeline_events.append({
                "date": event_date.strftime('%Y-%m-%d'),
                "title": result.get('title', 'Referenced Event'),
                "source": result.get('source', 'Unknown')
            })
    timeline_events.sort(key=lambda x: x['date'], reverse=True)

    all_possible_sources = ["LinkedIn", "Case/News", "Reddit", "Wikipedia", "Business", "Academic", "General"]
    source_counts = Counter(r['source'] for r in filtered_results)
    
    source_analysis = []
    for source in all_possible_sources:
        source_analysis.append({
            "name": source,
            "count": source_counts.get(source, 0)
        })

    raw_data_for_frontend = [
        {
            "title": r.get("title"),
            "snippet": r.get("snippet"),
            "link": r.get("link"),
            "source": r.get("source")
        } for r in filtered_results
    ]

    return {
        "name": name,
        "location": city,
        "short_summary": ai_analysis.get("short_summary"),
        "detailed_summary": ai_analysis.get("detailed_summary"),
        "riskAnalysis": ai_analysis.get("riskAnalysis"),
        "sourceAnalysis": source_analysis,
        "timelineEvents": timeline_events,
        "raw_data": raw_data_for_frontend
    }
