# # pylint: disable = invalid-name
# import os
# import uuid

# import streamlit as st
# from langchain_core.messages import HumanMessage

# from agents.agent import Agent


# def populate_envs(sender_email, receiver_email, subject):
#     os.environ['FROM_EMAIL'] = sender_email
#     os.environ['TO_EMAIL'] = receiver_email
#     os.environ['EMAIL_SUBJECT'] = subject


# def send_email(sender_email, receiver_email, subject, thread_id):
#     try:
#         populate_envs(sender_email, receiver_email, subject)
#         config = {'configurable': {'thread_id': thread_id}}
#         st.session_state.agent.graph.invoke(None, config=config)
#         st.success('Email sent successfully!')
#         # Clear session state
#         for key in ['travel_info', 'thread_id']:
#             st.session_state.pop(key, None)
#     except Exception as e:
#         st.error(f'Error sending email: {e}')


# def initialize_agent():
#     if 'agent' not in st.session_state:
#         st.session_state.agent = Agent()


# def render_custom_css():
#     st.markdown(
#         '''
#         <style>
#         .main-title {
#             font-size: 2.5em;
#             color: #333;
#             text-align: center;
#             margin-bottom: 0.5em;
#             font-weight: bold;
#         }
#         .sub-title {
#             font-size: 1.2em;
#             color: #333;
#             text-align: left;
#             margin-bottom: 0.5em;
#         }
#         .center-container {
#             display: flex;
#             flex-direction: column;
#             align-items: center;
#             width: 100%;
#         }
#         .query-box {
#             width: 80%;
#             max-width: 600px;
#             margin-top: 0.5em;
#             margin-bottom: 1em;
#         }
#         .query-container {
#             width: 80%;
#             max-width: 600px;
#             margin: 0 auto;
#         }
#         </style>
#         ''', unsafe_allow_html=True)


# def render_ui():
#     st.markdown('<div class="center-container">', unsafe_allow_html=True)
#     st.markdown('<div class="main-title">✈️🌍 AI Travel Agent 🏨🗺️</div>', unsafe_allow_html=True)
#     st.markdown('<div class="query-container">', unsafe_allow_html=True)
#     st.markdown('<div class="sub-title">Enter your travel query and get flight and hotel information:</div>', unsafe_allow_html=True)
#     user_input = st.text_area(
#         'Travel Query',
#         height=200,
#         key='query',
#         placeholder='Type your travel query here...',
#     )
#     st.markdown('</div>', unsafe_allow_html=True)
#     st.sidebar.image('images/ai-travel.png', caption='AI Travel Assistant')

#     return user_input


# def process_query(user_input):
#     if user_input:
#         try:
#             thread_id = str(uuid.uuid4())
#             st.session_state.thread_id = thread_id

#             messages = [HumanMessage(content=user_input)]
#             config = {'configurable': {'thread_id': thread_id}}

#             result = st.session_state.agent.graph.invoke({'messages': messages}, config=config)

#             st.subheader('Travel Information')
#             st.write(result['messages'][-1].content)

#             st.session_state.travel_info = result['messages'][-1].content

#         except Exception as e:
#             st.error(f'Error: {e}')
#     else:
#         st.error('Please enter a travel query.')


# def render_email_form():
#     send_email_option = st.radio('Do you want to send this information via email?', ('No', 'Yes'))
#     if send_email_option == 'Yes':
#         with st.form(key='email_form'):
#             sender_email = st.text_input('Sender Email')
#             receiver_email = st.text_input('Receiver Email')
#             subject = st.text_input('Email Subject', 'Travel Information')
#             submit_button = st.form_submit_button(label='Send Email')

#         if submit_button:
#             if sender_email and receiver_email and subject:
#                 send_email(sender_email, receiver_email, subject, st.session_state.thread_id)
#             else:
#                 st.error('Please fill out all email fields.')


# def main():
#     initialize_agent()
#     render_custom_css()
#     user_input = render_ui()

#     if st.button('Get Travel Information'):
#         process_query(user_input)

#     if 'travel_info' in st.session_state:
#         render_email_form()


# if __name__ == '__main__':
#     main()



# =======================================================
# pylint: disable=invalid-name
import os
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from agents.agent import Agent
import json
# NEW IMPORTS
from services.itinerary_generator import generate_itinerary
from services.budget_planner import analyze_budget
from database.db import SessionLocal, TravelHistory
from dotenv import load_dotenv
load_dotenv()
# Validate required API keys early so failures are clear
required_keys = [
    # Either OpenAI or Groq key is required for the conversational agent
    # we only enforce that at least one is present below
    "SERPAPI_API_KEY",     # used by various search tools
    # Other keys (WEATHER_API_KEY, SENDGRID_API_KEY) are optional and checked on demand
]

# make sure we have a model key
if not (os.getenv('OPENAI_API_KEY') or os.getenv('GROQ_API_KEY')):
    raise RuntimeError("Missing required environment variable: OPENAI_API_KEY or GROQ_API_KEY")
for key in required_keys:
    if not os.getenv(key):
        raise RuntimeError(f"Missing required environment variable: {key}")

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
    os.environ['FROM_EMAIL'] = sender_email
    os.environ['TO_EMAIL'] = receiver_email
    os.environ['EMAIL_SUBJECT'] = subject


# -----------------------------
# Routes
# -----------------------------

@app.post("/travel")
def travel(request: TravelRequest):
    try:
        print("📥 Received request:", request.query)

        thread_id = str(uuid.uuid4())

        messages = [HumanMessage(content=request.query)]
        config = {"configurable": {"thread_id": thread_id}}

        result = agent.graph.invoke(
            {"messages": messages},
            config=config
        )

        raw_output = result["messages"][-1].content.strip()

        # ✅ Try parsing structured JSON (future support)
        try:
            structured = json.loads(raw_output)
            return {
                "thread_id": thread_id,
                "data": structured,
                "format": "json"
            }
        except json.JSONDecodeError:
            # If not JSON, fallback to normal response
            return {
                "thread_id": thread_id,
                "response": raw_output,
                "format": "text"
            }

    except Exception as e:
        print("❌ ERROR INSIDE /travel:")
        print(str(e))

        detail = str(e)

        if "invalid_api_key" in detail or "Incorrect API key" in detail:
            raise HTTPException(
                status_code=401,
                detail="Model API key missing or invalid. " + detail
            )

        raise HTTPException(status_code=500, detail=detail)


@app.post("/send-email")
def send_email(request: EmailRequest):
    """
    Send email using stored travel information
    """
    try:
        populate_envs(request.sender_email, request.receiver_email, request.subject)

        config = {"configurable": {"thread_id": request.thread_id}}

        # Resume graph execution (email_sender node)
        agent.graph.invoke(None, config=config)

        return {"message": "Email sent successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-itinerary")
def itinerary(request: ItineraryRequest):
    """
    Generate AI itinerary
    """
    try:
        result = generate_itinerary(request.destination, request.days)
        return {"itinerary": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/budget-analysis")
def budget(request: BudgetRequest):
    """
    Analyze trip budget
    """
    try:
        result = analyze_budget(
            request.flight_cost,
            request.hotel_cost,
            request.budget
        )
        return {"budget_analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-price-alert")
def price_alert(request: PriceAlertRequest):
    """
    Dummy price alert endpoint
    (You can later connect this to background cron job)
    """
    try:
        return {
            "message": f"Price alert set for {request.route} at ${request.target_price}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/travel-history")
def travel_history():
    """
    Get stored travel queries
    """
    try:
        db = SessionLocal()
        records = db.query(TravelHistory).all()
        db.close()

        return {"history": [r.query for r in records]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/weather")
def get_weather():
    """
    Dummy weather endpoint
    """
    return {"message": "Weather data would be fetched here"}