# OSINT Investigator

This repo contains a real-time OSINT investigation tool. It performs live searches on public data (e.g. LinkedIn, news/case records) for a given name and city, applies NLP-based entity extraction, scores results, and saves structured JSON.

## 📂 Structure
- `model/` → Python OSINT engine (Google API, NLP, scoring, JSON export)


## 🚀 Model setup
cd model
pip install -r requirements.txt
python -m spacy download en_core_web_sm

Create a `.env` file in `model/`:
    GOOGLE_API_KEY=your_google_api_key_here
    GOOGLE_CSE_ID=your_google_cse_id_here


# Run the investigator:
    python osint_investigator.py

    
## 📝 Notes
- All results are saved as JSON files in the `model/` directory.
- Be sure `.env` is listed in `.gitignore` so your API keys remain secure.






