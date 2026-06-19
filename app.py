import csv, io, os, uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
_results_store: dict[str, list[dict]] = {}

PREFECTURES_CITIES = {
    "北海道":["札幌市中央区","札幌市北区","札幌市東区","函館市","旭川市","釧路市","帯広市","小樽市","苫小牧市"],
    "青森県":["青森市","弘前市","八戸市","五所川原市","十和田市","三沢市"],
    "岩手県":["盛岡市","宮古市","花巻市","北上市","一関市","釜石市","奥州市"],
    "宮城県":["仙台市青葉区","仙台市宮城野区","仙台市若林区","仙台市太白区","仙台市泉区","石巻市","気仙沼市","大崎市"],
    "秋田県":["秋田市","能代市","横手市","大館市","湯沢市","由利本荘市","大仙市"],
    "山形県":["山形市","米沢市","鶴岡市","酒田市","新庄市","天童市","東根市"],
    "福島県":["福島市","会津若松市","郡山市","いわき市","白河市","須賀川市","南相馬市"],
    "茨城県":["水戸市","日立市","土浦市","つくば市","ひたちなか市","古河市","取手市"],
    "栃木県":["宇都宮市","足利市","栃木市","佐野市","鹿沼市","日光市","小山市"],
    "群馬県":["前橋市","高崎市","桐生市","伊勢崎市","太田市","沼田市","館林市"],
    "埼玉県":["さいたま市大宮区","さいたま市浦和区","さいたま市中央区","川越市","熊谷市","川口市","所沢市","春日部市","越谷市","草加市"],
    "千葉県":["千葉市中央区","千葉市花見川区","千葉市稲毛区","千葉市美浜区","船橋市","松戸市","柏市","市川市","浦安市","成田市"],
    "東京都":["千代田区","中央区","港区","新宿区","文京区","台東区","墨田区","江東区","品川区","目黒区","大田区","世田谷区","渋谷区","中野区","杉並区","豊島区","北区","荒川区","板橋区","練馬区","足立区","葛飾区","江戸川区","八王子市","立川市","武蔵野市","三鷹市","府中市","調布市","町田市"],
    "神奈川県":["横浜市西区","横浜市中区","横浜市南区","横浜市港北区","横浜市青葉区","川崎市中原区","川崎市高津区","相模原市中央区","横須賀市","藤沢市","平塚市","鎌倉市","小田原市","茅ヶ崎市","厚木市","大和市"],
    "新潟県":["新潟市中央区","新潟市東区","新潟市西区","長岡市","三条市","柏崎市","上越市"],
    "富山県":["富山市","高岡市","魚津市","氷見市","射水市"],
    "石川県":["金沢市","七尾市","小松市","加賀市","白山市"],
    "福井県":["福井市","敦賀市","小浜市","鯖江市","越前市"],
    "山梨県":["甲府市","富士吉田市","山梨市","甲斐市","笛吹市"],
    "長野県":["長野市","松本市","上田市","飯田市","諏訪市","塩尻市","佐久市","安曇野市"],
    "岐阜県":["岐阜市","大垣市","高山市","多治見市","各務原市","可児市","郡上市"],
    "静岡県":["静岡市葵区","静岡市駿河区","静岡市清水区","浜松市中央区","沼津市","富士市","磐田市","焼津市","掛川市","藤枝市"],
    "愛知県":["名古屋市千種区","名古屋市東区","名古屋市北区","名古屋市西区","名古屋市中村区","名古屋市中区","名古屋市昭和区","名古屋市緑区","名古屋市名東区","名古屋市天白区","豊橋市","岡崎市","一宮市","豊田市","春日井市","刈谷市","安城市","西尾市","長久手市"],
    "三重県":["津市","四日市市","伊勢市","松阪市","桑名市","鈴鹿市","名張市","伊賀市"],
    "滋賀県":["大津市","彦根市","長浜市","草津市","守山市","栗東市","甲賀市","東近江市"],
    "京都府":["京都市北区","京都市上京区","京都市左京区","京都市中京区","京都市東山区","京都市下京区","京都市南区","京都市右京区","京都市伏見区","宇治市","亀岡市","長岡京市"],
    "大阪府":["大阪市都島区","大阪市此花区","大阪市西区","大阪市天王寺区","大阪市浪速区","大阪市東淀川区","大阪市城東区","大阪市住吉区","大阪市平野区","大阪市北区","大阪市中央区","堺市堺区","堺市北区","豊中市","吹田市","高槻市","枚方市","茨木市","八尾市","寝屋川市","東大阪市"],
    "兵庫県":["神戸市東灘区","神戸市灘区","神戸市兵庫区","神戸市長田区","神戸市須磨区","神戸市垂水区","神戸市北区","神戸市中央区","神戸市西区","姫路市","尼崎市","明石市","西宮市","芦屋市","伊丹市","宝塚市","川西市","三田市"],
    "奈良県":["奈良市","大和高田市","大和郡山市","橿原市","桜井市","生駒市","香芝市"],
    "和歌山県":["和歌山市","海南市","橋本市","有田市","田辺市","新宮市"],
    "鳥取県":["鳥取市","米子市","倉吉市","境港市"],
    "島根県":["松江市","浜田市","出雲市","益田市"],
    "岡山県":["岡山市北区","岡山市中区","岡山市南区","倉敷市","津山市","総社市","備前市"],
    "広島県":["広島市中区","広島市東区","広島市南区","広島市西区","広島市安佐南区","広島市安佐北区","呉市","福山市","尾道市","東広島市","廿日市市"],
    "山口県":["下関市","宇部市","山口市","防府市","岩国市","周南市","山陽小野田市"],
    "徳島県":["徳島市","鳴門市","阿南市","吉野川市","阿波市"],
    "香川県":["高松市","丸亀市","坂出市","善通寺市","観音寺市","さぬき市"],
    "愛媛県":["松山市","今治市","宇和島市","新居浜市","西条市","大洲市"],
    "高知県":["高知市","室戸市","南国市","土佐市","四万十市"],
    "福岡県":["福岡市博多区","福岡市中央区","福岡市南区","福岡市西区","福岡市早良区","北九州市小倉北区","北九州市八幡西区","久留米市","飯塚市","春日市","大野城市","太宰府市","糸島市"],
    "佐賀県":["佐賀市","唐津市","鳥栖市","伊万里市","武雄市"],
    "長崎県":["長崎市","佐世保市","島原市","諫早市","大村市"],
    "熊本県":["熊本市中央区","熊本市東区","熊本市西区","熊本市南区","熊本市北区","八代市","玉名市","菊池市","天草市"],
    "大分県":["大分市","別府市","中津市","日田市","佐伯市","宇佐市"],
    "宮崎県":["宮崎市","都城市","延岡市","日南市","小林市","日向市"],
    "鹿児島県":["鹿児島市","鹿屋市","薩摩川内市","霧島市","姶良市","奄美市"],
    "沖縄県":["那覇市","宜野湾市","石垣市","浦添市","名護市","沖縄市","うるま市","宮古島市"],
}

INDUSTRIES = [
    "ラーメン店","寿司店","居酒屋","焼肉店","カフェ・喫茶店","イタリアンレストラン",
    "中華料理店","フランス料理店","そば・うどん店","ファミリーレストラン",
    "弁当・テイクアウト","ケーキ・スイーツ店","パン屋","バー・ナイトクラブ",
    "美容院・ヘアサロン","理髪店・床屋","ネイルサロン","エステサロン",
    "マッサージ・整体","整骨院・接骨院","ジム・フィットネス","ヨガ・ピラティス",
    "歯科医院","内科クリニック","整形外科","皮膚科","眼科","耳鼻咽喉科",
    "小児科","産婦人科","精神科・心療内科","動物病院",
    "不動産会社","リフォーム会社","建設会社","引越し会社","住宅販売",
    "自動車販売店","自動車修理・整備","中古車販売","カーディーラー","ガソリンスタンド",
    "スーパーマーケット","コンビニエンスストア","ドラッグストア","書店",
    "家電量販店","ホームセンター","リサイクルショップ","花屋",
    "学習塾","英会話スクール","音楽教室","保育園・幼稚園","専門学校",
    "ホテル","旅館","民泊","観光スポット",
    "税理士事務所","社会保険労務士","行政書士","司法書士","弁護士事務所","保険会社・代理店",
    "ウェブ制作会社","システム開発会社","デザイン事務所","印刷会社","広告代理店",
    "クリーニング店","ペットショップ","ペットサロン","葬儀社","結婚式場・ブライダル",
    "写真スタジオ","旅行代理店",
]


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
    content = "﻿" + output.getvalue()
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=google_maps_list.csv"},
    )


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()
