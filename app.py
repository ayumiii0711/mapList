import csv
import io
import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from apify_client import ApifyClient
from dotenv import load_dotenv
from data.locations import PREFECTURES_CITIES, INDUSTRIES

load_dotenv()
app = FastAPI()
_results_store: dict[str, list[dict]] = {}


class SearchRequest(BaseModel):
    industry: str
    prefecture: str
    city: str
    max_results: int = 100


def scrape_google_maps(industry, prefecture, city, max_results=100):
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise ValueError("APIFY_TOKEN が設定されていません")
    client = ApifyClient(token)
    search_string = f"{industry} {city or prefecture}"
    run_input = {
        "searchStringsArray": [search_string],
        "maxCrawledPlacesPerSearch": max_results,
        "language": "ja",
        "exportPlaceUrls": True,
        "additionalInfo": False,
        "reviews": False,
        "photos": False,
    }
    run = client.actor("compass/google-maps-scraper").call(run_input=run_input)
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append({
            "店名": item.get("title", ""),
            "住所": item.get("address", ""),
            "電話番号": item.get("phone", ""),
            "URL": item.get("url", ""),
        })
    return results


@app.get("/api/industries")
def get_industries():
    return INDUSTRIES


@app.get("/api/prefectures")
def get_prefectures():
    return list(PREFECTURES_CITIES.keys())


@app.get("/api/cities/{prefecture}")
def get_cities(prefecture: str):
    cities = PREFECTURES_CITIES.get(prefecture)
    if cities is None:
        raise HTTPException(status_code=404, detail="Prefecture not found")
    return cities


@app.post("/api/search")
def search(req: SearchRequest):
    if not req.industry or not req.prefecture:
        raise HTTPException(status_code=400, detail="業種と都道府県は必須です")
    try:
        results = scrape_google_maps(req.industry, req.prefecture, req.city, req.max_results)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"スクレイピングエラー: {e}")
    session_id = str(uuid.uuid4())
    _results_store[session_id] = results
    return {"session_id": session_id, "count": len(results), "results": results}


@app.get("/api/download/{session_id}")
def download_csv(session_id: str):
    results = _results_store.get(session_id)
    if results is None:
        raise HTTPException(status_code=404, detail="データが見つかりません。再度検索してください。")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["店名", "住所", "電話番号", "URL"])
    writer.writeheader()
    writer.writerows(results)
    output.seek(0)
    content = "\ufeff" + output.getvalue()
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=google_maps_list.csv"},
    )


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()
