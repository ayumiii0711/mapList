import csv
import io
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from data.locations import PREFECTURES_CITIES, INDUSTRIES
from src.apify_scraper import scrape_google_maps

app = FastAPI()

_results_store: dict[str, list[dict]] = {}


class SearchRequest(BaseModel):
    industry: str
    prefecture: str
    city: str
    max_results: int = 100


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
