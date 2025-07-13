import requests
import spacy
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import re
import google.generativeai as genai
import threading
import time
from rapidfuzz import fuzz, process 

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-pro")
nlp = spacy.load("en_core_web_sm")

# Global progress store reference
progress_store = {}

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

def cached_name_match(target_name, entities_tuple):
    entities = [{"text": ent[0], "label": ent[1]} for ent in entities_tuple]
    target_parts = [part.lower() for part in target_name.split() if part.strip()]

    if len(target_parts) < 2:
        target = target_parts[0]
        for ent in entities:
            if ent['label'] == 'PERSON':
                person_name = ent['text'].lower()
                if target in person_name or person_name in target:
                    return True
    else:
        for ent in entities:
            if ent['label'] == 'PERSON':
                person_name = ent['text'].lower()
                if all(part in person_name for part in target_parts):
                    return True
    return False

def is_name_match(target_name, entities):
    entities_tuple = tuple((ent["text"], ent["label"]) for ent in entities)
    return cached_name_match(target_name, entities_tuple)

def gemini_summarize_with_progress(name, city, extras, title, snippet, link, entities, search_id=None):
    if search_id and search_id in progress_store:
        progress_store[search_id].update({"percentage": 75, "stage": "Processing with Gemini AI..."})

    extras_text = ", ".join(extras) if extras else "N/A"
    entity_summary = "\n".join([f'- {e["label"]}: {e["text"]}' for e in entities])

    prompt = f"""Search about {name}, {city}, {extras_text} on the web and integrate a summary using:
    Title: {title}
    Snippet: "{snippet}"
    Entities:
    {entity_summary}
    Link: {link}

Generate a clear, concise summary suitable for an OSINT investigation report.
"""
    try:
        if search_id and search_id in progress_store:
            progress_store[search_id].update({"percentage": 78, "stage": "Analyzing content..."})
        time.sleep(0.2)
        if search_id and search_id in progress_store:
            progress_store[search_id].update({"percentage": 82, "stage": "Generating insights..."})
        response = model.generate_content(prompt)
        if search_id and search_id in progress_store:
            progress_store[search_id].update({"percentage": 88, "stage": "Finalizing summary..."})
        time.sleep(0.2)
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        if search_id and search_id in progress_store:
            progress_store[search_id].update({"percentage": 85, "stage": "Using fallback summary..."})
        return f"Based on available information about {name} from {city}: {snippet[:200]}..."

def run_osint_with_progress(name, city, extras, search_id=None):
    global progress_store

    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise ValueError("Missing Google API key or CSE ID in .env")

    extra_text = " ".join(extras)

    if search_id and search_id in progress_store:
        progress_store[search_id].update({"percentage": 15, "stage": "Searching LinkedIn profiles..."})

    linkedin_query = f'site:linkedin.com/in {name} {city} {extra_text}'
    linkedin_results = google_api_search(linkedin_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="LinkedIn")

    if search_id and search_id in progress_store:
        progress_store[search_id].update({"percentage": 35, "stage": "Searching news sources..."})

    case_keywords = 'crime OR FIR OR arrested OR chargesheet OR court OR case site:ndtv.com OR site:thehindu.com OR site:indiatoday.in OR site:barandbench.com OR site:livelaw.in'
    news_query = f'{name} {city} {case_keywords} {extra_text}'
    case_results = google_api_search(news_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="Case/News")

    if search_id and search_id in progress_store:
        progress_store[search_id].update({"percentage": 55, "stage": "Collecting general information..."})

    general_query = f'{name} {city} {extra_text}'
    general_results = google_api_search(general_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="General")

    if search_id and search_id in progress_store:
        progress_store[search_id].update({"percentage": 65, "stage": "Processing search results..."})

    combined = merge_and_dedupe(linkedin_results + case_results + general_results)
    if not combined:
        print("⚠️ No search results found for the queries.")
        return [{"error": "No relevant search results found for the given name and city."}]

    if search_id and search_id in progress_store:
        progress_store[search_id].update({"percentage": 70, "stage": "Analyzing content with NLP..."})

    combined = enrich_with_nlp(combined)

    # ---------- Improved Filtering ----------
    filtered_results = []

    name_tokens = [t for t in name.split() if t.strip()]
    name_lower   = " ".join(name_tokens).lower()

    if name_tokens:
        if len(name_tokens) >= 2:
            full_name_regex = re.compile(r'\b' + r'\s+'.join(map(re.escape, name_tokens)) + r'\b', re.I)
        else:
            full_name_regex = re.compile(r'\b' + re.escape(name_tokens[0]) + r'\b', re.I)
    else:
        full_name_regex = None

    for result in combined:
        title   = result.get("title",   "")
        snippet = result.get("snippet", "")
        raw     = f"{title} {snippet}"
        raw_low = raw.lower()

    # 1️ spaCy entity
        if is_name_match(name, result["entities"]):
            filtered_results.append(result)
            continue

    # 2️ exact phrase
        if full_name_regex and (full_name_regex.search(title) or full_name_regex.search(snippet)):
            filtered_results.append(result)
            print(f"✅ Included via exact phrase: {title}")
            continue

    # 3️ fuzzy full‑name match (≥90)
        if fuzz.partial_ratio(name_lower, raw_low) >= 90:
            filtered_results.append(result)
            print(f"✅ Included via fuzzy full‑name: {title}")
            continue

    # 4️ fuzzy token‑by‑token (every token ≥85)
        token_hits = [
            fuzz.partial_ratio(tok.lower(), raw_low) >= 85
            for tok in name_tokens
            if tok
        ]
        if token_hits and all(token_hits):
            filtered_results.append(result)
            print(f"✅ Included via fuzzy tokens: {title}")
        else:
            print(f"⚠️ Skipped irrelevant result: {title}")

    if not filtered_results:
        print("❌ No person match found in any search results.")
        return [{"error": "No data found matching the person. They may not have a public profile or presence."}]

    # ---------- Single Gemini call ----------
    if filtered_results:
        if search_id and search_id in progress_store:
            progress_store[search_id].update({"percentage": 75, "stage": "Processing top result with AI..."})

        first = filtered_results[0]
        first_summary = gemini_summarize_with_progress(
            name, city, extras,
            first['title'], first['snippet'], first['link'], first['entities'],
            search_id
        )
        first["gemini_summary"] = first_summary or "Summary not available."

        for r in filtered_results[1:]:
            r["gemini_summary"] = (
                (r["snippet"][:200] + "...") if r.get("snippet") else
                "Gemini summary skipped to conserve API calls."
            )

    return filtered_results

# Backward‑compat wrapper
def run_osint(name, city, extras):
    return run_osint_with_progress(name, city, extras, None)




# import requests
# import spacy
# import json
# from datetime import datetime
# from dotenv import load_dotenv
# import os
# import re
# import google.generativeai as genai

# load_dotenv()

# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# genai.configure(api_key=GEMINI_API_KEY)
# model = genai.GenerativeModel("models/gemini-2.5-pro")
# nlp = spacy.load("en_core_web_sm")

# def safe_filename(text):
#     return re.sub(r'[^A-Za-z0-9_]+', '_', text)

# def google_api_search(query, api_key, cse_id, max_results=100, tag=""):
#     url = "https://www.googleapis.com/customsearch/v1"
#     results = []
#     start = 1
#     while len(results) < max_results:
#         params = {
#             "q": query,
#             "key": api_key,
#             "cx": cse_id,
#             "num": min(10, max_results - len(results)),
#             "start": start,
#             "gl": "in",
#             "hl": "en"
#         }
#         resp = requests.get(url, params=params)
#         if resp.status_code != 200:
#             print(f"❌ Google API error {resp.status_code}: {resp.text}")
#             break
#         items = resp.json().get("items", [])
#         if not items:
#             break
#         for item in items:
#             results.append({
#                 "source": tag,
#                 "title": item.get("title"),
#                 "link": item.get("link"),
#                 "snippet": item.get("snippet", "")
#             })
#         start += len(items)
#     print(f"✅ {tag} search got {len(results)} results for query: {query}")
#     return results

# def merge_and_dedupe(results):
#     seen = set()
#     deduped = []
#     for r in results:
#         link = r.get("link")
#         if link and link not in seen:
#             seen.add(link)
#             deduped.append(r)
#     return deduped

# def enrich_with_nlp(results):
#     for r in results:
#         text = f"{r.get('title', '')}. {r.get('snippet', '')}"
#         doc = nlp(text)
#         r["entities"] = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
#     return results

# def is_name_match(target_name, entities):
#     target_parts = [part.lower() for part in target_name.split() if part.strip()]
#     if len(target_parts) < 2:
#         target = target_parts[0]
#         for ent in entities:
#             if ent['label'] == 'PERSON':
#                 person_name = ent['text'].lower()
#                 if target in person_name or person_name in target:
#                     return True
#     else:
#         for ent in entities:
#             if ent['label'] == 'PERSON':
#                 person_name = ent['text'].lower()
#                 if all(part in person_name for part in target_parts):
#                     return True
#     return False

# def gemini_summarize(name, city, extras, title, snippet, link, entities):
#     extras_text = ", ".join(extras) if extras else "N/A"
#     entity_summary = "\n".join([f'- {e["label"]}: {e["text"]}' for e in entities])
#     prompt = f"""Search about {name}, {city}, {extras_text} on the web and integrate a summary using:
#     Title: {title}
#     Snippet: "{snippet}"
#     Entities:
#     {entity_summary}
#     Link: {link}

# Generate a clear, concise summary suitable for an OSINT investigation report.
# """
#     try:
#         response = model.generate_content(prompt)
#         return response.text
#     except Exception as e:
#         print(f"Gemini error: {e}")
#         return None

# def run_osint(name, city, extras):
#     if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
#         raise ValueError("Missing Google API key or CSE ID in .env")

#     extra_text = " ".join(extras)

#     linkedin_query = f'site:linkedin.com/in {name} {city} {extra_text}'
#     case_keywords = 'crime OR FIR OR arrested OR chargesheet OR court OR case site:ndtv.com OR site:thehindu.com OR site:indiatoday.in OR site:barandbench.com OR site:livelaw.in'
#     news_query = f'{name} {city} {case_keywords} {extra_text}'
#     general_query = f'{name} {city} {extra_text}'

#     linkedin_results = google_api_search(linkedin_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="LinkedIn")
#     case_results = google_api_search(news_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="Case/News")
#     general_results = google_api_search(general_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="General")

#     combined = merge_and_dedupe(linkedin_results + case_results + general_results)
#     if not combined:
#         print("⚠️ No search results found for the queries.")
#         return [{"error": "No relevant search results found for the given name and city."}]

#     combined = enrich_with_nlp(combined)

#     filtered_results = []
#     for result in combined:
#         if is_name_match(name, result['entities']):
#             filtered_results.append(result)
#         else:
#             print(f"⚠️ Skipped irrelevant result: {result.get('title')}")

#     if not filtered_results:
#         print("❌ No person match found in any search results.")
#         return [{"error": "No data found matching the person. They may not have a public profile or presence."}]

#     for r in filtered_results:
#         summary = gemini_summarize(name, city, extras, r['title'], r['snippet'], r['link'], r['entities'])
#         r["gemini_summary"] = summary or "Summary not available."

#     return filtered_results

# import requests
# import spacy
# import json
# from datetime import datetime
# from dotenv import load_dotenv
# import os
# import re
# import google.generativeai as genai
# import threading
# import time

# load_dotenv()

# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# genai.configure(api_key=GEMINI_API_KEY)
# model = genai.GenerativeModel("models/gemini-2.5-pro")
# nlp = spacy.load("en_core_web_sm")

# # Global progress store reference
# progress_store = {}

# def safe_filename(text):
#     return re.sub(r'[^A-Za-z0-9_]+', '_', text)

# def google_api_search(query, api_key, cse_id, max_results=100, tag=""):
#     url = "https://www.googleapis.com/customsearch/v1"
#     results = []
#     start = 1
#     while len(results) < max_results:
#         params = {
#             "q": query,
#             "key": api_key,
#             "cx": cse_id,
#             "num": min(10, max_results - len(results)),
#             "start": start,
#             "gl": "in",
#             "hl": "en"
#         }
#         resp = requests.get(url, params=params)
#         if resp.status_code != 200:
#             print(f"❌ Google API error {resp.status_code}: {resp.text}")
#             break
#         items = resp.json().get("items", [])
#         if not items:
#             break
#         for item in items:
#             results.append({
#                 "source": tag,
#                 "title": item.get("title"),
#                 "link": item.get("link"),
#                 "snippet": item.get("snippet", "")
#             })
#         start += len(items)
#     print(f"✅ {tag} search got {len(results)} results for query: {query}")
#     return results

# def merge_and_dedupe(results):
#     seen = set()
#     deduped = []
#     for r in results:
#         link = r.get("link")
#         if link and link not in seen:
#             seen.add(link)
#             deduped.append(r)
#     return deduped

# def enrich_with_nlp(results):
#     for r in results:
#         text = f"{r.get('title', '')}. {r.get('snippet', '')}"
#         doc = nlp(text)
#         r["entities"] = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
#     return results

# def is_name_match(target_name, entities):
#     target_parts = [part.lower() for part in target_name.split() if part.strip()]
#     if len(target_parts) < 2:
#         target = target_parts[0]
#         for ent in entities:
#             if ent['label'] == 'PERSON':
#                 person_name = ent['text'].lower()
#                 if target in person_name or person_name in target:
#                     return True
#     else:
#         for ent in entities:
#             if ent['label'] == 'PERSON':
#                 person_name = ent['text'].lower()
#                 if all(part in person_name for part in target_parts):
#                     return True
#     return False

# def gemini_summarize_with_progress(name, city, extras, title, snippet, link, entities, search_id=None):
#     """Enhanced Gemini summarization with progress tracking"""
    
#     # Update progress for Gemini processing start
#     if search_id and search_id in progress_store:
#         progress_store[search_id].update({"percentage": 75, "stage": "Processing with Gemini AI..."})
    
#     extras_text = ", ".join(extras) if extras else "N/A"
#     entity_summary = "\n".join([f'- {e["label"]}: {e["text"]}' for e in entities])
    
#     prompt = f"""Search about {name}, {city}, {extras_text} on the web and integrate a summary using:
#     Title: {title}
#     Snippet: "{snippet}"
#     Entities:
#     {entity_summary}
#     Link: {link}

# Generate a clear, concise summary suitable for an OSINT investigation report.
# """
    
#     try:
#         # Update progress for content analysis
#         if search_id and search_id in progress_store:
#             progress_store[search_id].update({"percentage": 78, "stage": "Analyzing content..."})
        
#         # Add a small delay to show progress
#         time.sleep(0.2)
        
#         # Update progress for AI processing
#         if search_id and search_id in progress_store:
#             progress_store[search_id].update({"percentage": 82, "stage": "Generating insights..."})
        
#         # Make the actual Gemini call
#         response = model.generate_content(prompt)
        
#         # Update progress for finalizing
#         if search_id and search_id in progress_store:
#             progress_store[search_id].update({"percentage": 88, "stage": "Finalizing summary..."})
        
#         time.sleep(0.2)  # Small delay to show progress
        
#         return response.text
        
#     except Exception as e:
#         print(f"Gemini error: {e}")
        
#         # Update progress for error or fallback
#         if search_id and search_id in progress_store:
#             progress_store[search_id].update({"percentage": 85, "stage": "Using fallback summary..."})
        
#         # Return a fallback summary based on the snippet
#         return f"Based on available information about {name} from {city}: {snippet[:200]}..."

# def run_osint_with_progress(name, city, extras, search_id=None):
#     """Enhanced OSINT function with detailed progress tracking"""
    
#     global progress_store
    
#     if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
#         raise ValueError("Missing Google API key or CSE ID in .env")

#     extra_text = " ".join(extras)

#     # Update progress for LinkedIn search
#     if search_id and search_id in progress_store:
#         progress_store[search_id].update({"percentage": 15, "stage": "Searching LinkedIn profiles..."})

#     linkedin_query = f'site:linkedin.com/in {name} {city} {extra_text}'
#     linkedin_results = google_api_search(linkedin_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="LinkedIn")
    
#     # Update progress for news search
#     if search_id and search_id in progress_store:
#         progress_store[search_id].update({"percentage": 35, "stage": "Searching news sources..."})
    
#     case_keywords = 'crime OR FIR OR arrested OR chargesheet OR court OR case site:ndtv.com OR site:thehindu.com OR site:indiatoday.in OR site:barandbench.com OR site:livelaw.in'
#     news_query = f'{name} {city} {case_keywords} {extra_text}'
#     case_results = google_api_search(news_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="Case/News")
    
#     # Update progress for general search
#     if search_id and search_id in progress_store:
#         progress_store[search_id].update({"percentage": 55, "stage": "Collecting general information..."})
    
#     general_query = f'{name} {city} {extra_text}'
#     general_results = google_api_search(general_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, max_results=5, tag="General")

#     # Update progress for processing results
#     if search_id and search_id in progress_store:
#         progress_store[search_id].update({"percentage": 65, "stage": "Processing search results..."})

#     combined = merge_and_dedupe(linkedin_results + case_results + general_results)
    
#     if not combined:
#         print("⚠️ No search results found for the queries.")
#         return [{"error": "No relevant search results found for the given name and city."}]

#     # Update progress for NLP processing
#     if search_id and search_id in progress_store:
#         progress_store[search_id].update({"percentage": 70, "stage": "Analyzing content with NLP..."})

#     combined = enrich_with_nlp(combined)

#     filtered_results = []
#     for result in combined:
#         if is_name_match(name, result['entities']):
#             filtered_results.append(result)
#         else:
#             print(f"⚠️ Skipped irrelevant result: {result.get('title')}")

#     if not filtered_results:
#         print("❌ No person match found in any search results.")
#         return [{"error": "No data found matching the person. They may not have a public profile or presence."}]

#     # Process each result with Gemini (with progress updates)
#     for i, r in enumerate(filtered_results):
#         # Update progress for each Gemini call
#         base_progress = 75 + (i * 10 / len(filtered_results))  # Distribute remaining 15% across results
        
#         if search_id and search_id in progress_store:
#             progress_store[search_id].update({
#                 "percentage": int(base_progress), 
#                 "stage": f"Processing result {i+1}/{len(filtered_results)} with AI..."
#             })
        
#         summary = gemini_summarize_with_progress(
#             name, city, extras, r['title'], r['snippet'], r['link'], r['entities'], search_id
#         )
#         r["gemini_summary"] = summary or "Summary not available."

#     return filtered_results

# # Keep the original function for backward compatibility
# def run_osint(name, city, extras):
#     """Original OSINT function without progress tracking"""
#     return run_osint_with_progress(name, city, extras, None)


