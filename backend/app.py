# =======================================================
# pylint: disable=invalid-name

import os
import uuid
import json
import traceback
import datetime
import requests
from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from serpapi import GoogleSearch

from agents.agent import Agent
from services.itinerary_generator import generate_itinerary
from services.budget_planner import analyze_budget
from database.db import SessionLocal, TravelHistory

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()

# -----------------------------
# Validate Required API Keys
# -----------------------------
required_keys = ["SERPAPI_API_KEY"]

if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
    raise RuntimeError(
        "Missing required environment variable: OPENAI_API_KEY or GROQ_API_KEY"
    )

for key in required_keys:
    if not os.getenv(key):
        raise RuntimeError(f"Missing required environment variable: {key}")

# -----------------------------
# FastAPI App + CORS + Agent
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = Agent()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
    )

# -----------------------------
# Request Models
# -----------------------------
class TravelRequest(BaseModel):
    query: str

class EmailRequest(BaseModel):
    sender_email: str
    receiver_email: str
    subject: str
    thread_id: str

class ItineraryRequest(BaseModel):
    destination: str
    days: int

class BudgetRequest(BaseModel):
    flight_cost: Optional[float] = None
    hotel_cost: Optional[float] = None
    budget: Optional[float] = None
    travel_data: Optional[dict[str, Any]] = None

class WeatherRequest(BaseModel):
    city: str
    date: Optional[str] = None

class VisaInfoRequest(BaseModel):
    nationality: str
    destination: str

class PriceAlertRequest(BaseModel):
    route: str
    target_price: float

# -----------------------------
# Helper Functions
# -----------------------------
def populate_envs(sender_email, receiver_email, subject):
    os.environ["FROM_EMAIL"] = sender_email
    os.environ["TO_EMAIL"] = receiver_email
    os.environ["EMAIL_SUBJECT"] = subject

def safe_json_parse(content):
    if content is None:
        return {"type": "empty", "data": None, "warning": "Agent returned None"}
    if isinstance(content, (dict, list)):
        return {"type": "structured", "data": content}
    if not isinstance(content, str):
        return {"type": "text", "data": str(content), "warning": "Agent response was not a string/dict/list"}
    content = content.strip()
    if not content:
        return {"type": "empty", "data": None, "warning": "Agent returned blank response"}
    try:
        return {"type": "structured", "data": json.loads(content)}
    except json.JSONDecodeError:
        return {"type": "text", "data": content, "warning": "Agent response was not valid JSON"}

def _coerce_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def _extract_budget_from_travel_data(travel_data):
    flights = travel_data.get("flights") if isinstance(travel_data, dict) else []
    hotels = travel_data.get("hotels") if isinstance(travel_data, dict) else []

    flight_cost = sum(_coerce_float(f.get("price") or f.get("total_price") or f.get("flight_cost") or 0) for f in flights)
    hotel_cost = sum(_coerce_float(h.get("total_price") or h.get("price") or h.get("price_per_night") or 0) for h in hotels)

    return round(flight_cost, 2), round(hotel_cost, 2)

def _build_budget_response(flight_cost, hotel_cost, budget):
    flight_cost = _coerce_float(flight_cost) or 0.0
    hotel_cost = _coerce_float(hotel_cost) or 0.0
    total_cost = round(flight_cost + hotel_cost, 2)
    if budget is None or budget == "":
        budget = total_cost
    budget = _coerce_float(budget) or total_cost
    remaining = round(budget - total_cost, 2)
    progress = 0 if budget <= 0 else min(100, round((total_cost / budget) * 100, 2))
    return {"flight_cost": flight_cost, "hotel_cost": hotel_cost, "total_cost": total_cost,
            "budget": budget, "remaining": remaining, "progress": progress}

# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def root():
    return {"message": "AI Travel Agent Backend is running"}

@app.post("/travel")
def process_query(request: TravelRequest):
    try:
        thread_id = str(uuid.uuid4())
        messages = [HumanMessage(content=request.query)]
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 10}
        result = agent.graph.invoke({"messages": messages}, config=config)
        if not result:
            return {"type": "empty", "thread_id": thread_id, "error": "Agent returned no result"}
        if "messages" not in result or not result["messages"]:
            return {"type": "empty", "thread_id": thread_id, "error": "Agent result missing messages", "raw_result": str(result)}
        last_message = result["messages"][-1]
        raw_output = getattr(last_message, "content", None)
        parsed_output = safe_json_parse(raw_output)
        response = {"type": parsed_output.get("type"), "thread_id": thread_id, "data": parsed_output.get("data")}
        if parsed_output.get("warning"):
            response["warning"] = parsed_output.get("warning")
        response["raw_output"] = raw_output
        return response
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-email")
def send_email(request: EmailRequest):
    try:
        populate_envs(request.sender_email, request.receiver_email, request.subject)
        config = {"configurable": {"thread_id": request.thread_id}, "recursion_limit": 10}
        agent.graph.invoke(None, config=config)
        return {"message": "Email sent successfully"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-itinerary")
def itinerary(request: ItineraryRequest):
    try:
        result = generate_itinerary(request.destination, request.days)
        return {"itinerary": result}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/budget-analysis")
def budget(request: BudgetRequest):
    try:
        flight_cost = request.flight_cost
        hotel_cost = request.hotel_cost
        if (flight_cost is None or hotel_cost is None) and request.travel_data:
            f_cost, h_cost = _extract_budget_from_travel_data(request.travel_data)
            flight_cost = flight_cost if flight_cost is not None else f_cost
            hotel_cost = hotel_cost if hotel_cost is not None else h_cost
        budget_summary = _build_budget_response(flight_cost, hotel_cost, request.budget)
        result = analyze_budget(budget_summary["flight_cost"], budget_summary["hotel_cost"], budget_summary["budget"])
        return {"status": "success", "message": result, "data": budget_summary}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/weather")
def weather(request: WeatherRequest):
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return {"status": "error", "message": "WEATHER_API_KEY missing", "data": {}}
    if not request.city:
        return {"status": "error", "message": "City is required", "data": {}}
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast"
        params = {"q": request.city, "appid": api_key, "units": "metric"}
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return {"status": "error", "message": "Failed to fetch weather", "data": {}}
        data = resp.json()
        forecast_list = data.get("list", [])
        if not forecast_list:
            return {"status": "error", "message": "No forecast data", "data": {}}
        target_date = request.date or forecast_list[0].get("dt_txt", "")[:10]
        forecast_item = next((i for i in forecast_list if i.get("dt_txt", "").startswith(target_date)), forecast_list[0])
        return {
            "status": "success",
            "message": f"Forecast for {request.city} on {target_date}",
            "data": {
                "city": request.city,
                "date": target_date,
                "temperature": forecast_item.get("main", {}).get("temp"),
                "description": forecast_item.get("weather", [{}])[0].get("description"),
                "humidity": forecast_item.get("main", {}).get("humidity"),
                "wind_speed": forecast_item.get("wind", {}).get("speed"),
            },
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/visa-info")
def visa_info(request: VisaInfoRequest):
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {"status": "error", "message": "SERPAPI_API_KEY missing", "data": {}}
    try:
        params = {
            "engine": "google",
            "q": f"Do {request.nationality} passport holders need visa for {request.destination}?",
            "hl": "en",
            "gl": "us",
            "api_key": api_key,
        }
        search = GoogleSearch(params)
        raw_results = search.get_dict()
        organic_results = raw_results.get("organic_results", []) if isinstance(raw_results, dict) else []
        if not organic_results:
            return {"status": "no_results", "message": "No visa information found.", "data": {}}
        top_result = organic_results[0]
        return {
            "status": "success",
            "message": f"Visa information summary for {request.nationality} to {request.destination}.",
            "data": {
                "nationality": request.nationality,
                "destination": request.destination,
                "summary": top_result.get("snippet") or top_result.get("title") or "Visa guidance available from search results.",
                "source": top_result.get("link") or top_result.get("displayed_link"),
            },
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-price-alert")
def price_alert(request: PriceAlertRequest):
    try:
        return {"message": f"Price alert set for {request.route} at ${request.target_price}"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/travel-history")
def travel_history():
    db = None
    try:
        db = SessionLocal()
        records = db.query(TravelHistory).all()
        return {"history": [r.query for r in records]}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if db:
            db.close()