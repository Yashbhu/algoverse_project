from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime
import json
from osint_investigator import search_person, generate_report_file

app = FastAPI(title="OSINT Search API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://osint-blue.vercel.app"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    name: str
    city: str
    extraTerms: str = ""

class ReportRequest(BaseModel):
    personData: dict

@app.get("/")
async def root():
    return {"message": "OSINT Search API is running"}

@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    try:
        # Parse extra terms
        extra_terms = [term.strip() for term in request.extraTerms.split(",") if term.strip()]
        
        # Call the search function
        results = search_person(request.name, request.city, extra_terms)
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found")
        
        # Create summary data for frontend
        summary_data = {
            "name": request.name,
            "location": request.city,
            "summary": f"Found {len(results)} relevant results for {request.name}. " + 
                      (results[0].get('gemini_summary', 'No summary available') if results else ''),
            "confidence": f"{min(95, max(60, len(results) * 10))}%",
            "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
            "totalResults": len(results),
            "results": results
        }
        
        return {"success": True, "data": summary_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/generate-report")
async def generate_report_endpoint(request: ReportRequest):
    try:
        # Generate report file
        report_path = generate_report_file(request.personData)
        
        return {
            "success": True, 
            "message": "Report generated successfully",
            "reportPath": report_path,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)