# =======================================================
# pylint: disable=invalid-name

import os
import uuid
import json
import traceback
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

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

required_keys = [
    "SERPAPI_API_KEY",
]

if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
    raise RuntimeError(
        "Missing required environment variable: OPENAI_API_KEY or GROQ_API_KEY"
    )

for key in required_keys:
    if not os.getenv(key):
        raise RuntimeError(f"Missing required environment variable: {key}")


# -----------------------------
# FastAPI App + Agent
# -----------------------------

app = FastAPI()
agent = Agent()


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
    flight_cost: float
    hotel_cost: float
    budget: float


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
    """
    Safely parse agent/model response.

    The agent may return:
    - valid JSON string
    - normal plain text
    - empty string
    - dict/list
    This prevents json.loads() from crashing the API.
    """

    if content is None:
        return {
            "type": "empty",
            "data": None,
            "warning": "Agent returned None"
        }

    if isinstance(content, (dict, list)):
        return {
            "type": "structured",
            "data": content
        }

    if not isinstance(content, str):
        return {
            "type": "text",
            "data": str(content),
            "warning": "Agent response was not a string/dict/list"
        }

    content = content.strip()

    if not content:
        return {
            "type": "empty",
            "data": None,
            "warning": "Agent returned blank response"
        }

    try:
        return {
            "type": "structured",
            "data": json.loads(content)
        }
    except json.JSONDecodeError:
        return {
            "type": "text",
            "data": content,
            "warning": "Agent response was not valid JSON"
        }


# -----------------------------
# Routes
# -----------------------------

@app.get("/")
def root():
    return {
        "message": "AI Travel Agent Backend is running"
    }


@app.post("/travel")
def process_query(request: TravelRequest):
    """
    Process travel query using LangGraph agent.
    Handles both JSON and plain text responses safely.
    """

    try:
        thread_id = str(uuid.uuid4())

        messages = [
            HumanMessage(content=request.query)
        ]

        config = {
            "configurable": {
                "thread_id": thread_id
            },
            "recursion_limit": 10
        }

        result = agent.graph.invoke(
            {"messages": messages},
            config=config
        )

        if not result:
            return {
                "type": "empty",
                "thread_id": thread_id,
                "error": "Agent returned no result"
            }

        if "messages" not in result or not result["messages"]:
            return {
                "type": "empty",
                "thread_id": thread_id,
                "error": "Agent result does not contain messages",
                "raw_result": str(result)
            }

        last_message = result["messages"][-1]
        raw_output = getattr(last_message, "content", None)

        parsed_output = safe_json_parse(raw_output)

        response = {
            "type": parsed_output.get("type"),
            "thread_id": thread_id,
            "data": parsed_output.get("data")
        }

        if parsed_output.get("warning"):
            response["warning"] = parsed_output.get("warning")

        # Helpful during frontend/backend debugging
        response["raw_output"] = raw_output

        return response

    except Exception as e:
        traceback.print_exc()
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send-email")
def send_email(request: EmailRequest):
    """
    Send email using stored travel information.
    """

    try:
        populate_envs(
            request.sender_email,
            request.receiver_email,
            request.subject
        )

        config = {
            "configurable": {
                "thread_id": request.thread_id
            },
            "recursion_limit": 10
        }

        agent.graph.invoke(None, config=config)

        return {
            "message": "Email sent successfully"
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-itinerary")
def itinerary(request: ItineraryRequest):
    """
    Generate AI itinerary.
    """

    try:
        result = generate_itinerary(
            request.destination,
            request.days
        )

        return {
            "itinerary": result
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/budget-analysis")
def budget(request: BudgetRequest):
    """
    Analyze trip budget.
    """

    try:
        result = analyze_budget(
            request.flight_cost,
            request.hotel_cost,
            request.budget
        )

        return {
            "budget_analysis": result
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-price-alert")
def price_alert(request: PriceAlertRequest):
    """
    Dummy price alert endpoint.
    You can later connect this to a background job or cron.
    """

    try:
        return {
            "message": f"Price alert set for {request.route} at ${request.target_price}"
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/travel-history")
def travel_history():
    """
    Get stored travel queries.
    """

    db = None

    try:
        db = SessionLocal()
        records = db.query(TravelHistory).all()

        return {
            "history": [record.query for record in records]
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if db:
            db.close()


@app.get("/weather")
def get_weather(city: str):
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return {"warning": "WEATHER_API_KEY missing"}
    
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    resp = requests.get(url)
    if resp.status_code != 200:
        return {"warning": "Failed to fetch weather"}
    data = resp.json()
    # Extract first day's weather
    return {"city": city, "forecast": data["list"][0]["main"]}