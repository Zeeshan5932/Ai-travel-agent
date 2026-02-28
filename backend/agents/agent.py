#pylint: disable = http-used,print-used,no-self-use
# pylint: disable=http-used,print-used,no-self-use
import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import datetime
import operator
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load .env
load_dotenv()

# EXISTING TOOLS
from agents.tools.flights_finder import flights_finder
from agents.tools.hotels_finder import hotels_finder
from agents.tools.weather_finder import weather_finder
from agents.tools.visa_checker import visa_checker
from agents.tools.cars_finder import cars_finder

CURRENT_YEAR = datetime.datetime.now().year

print("Loaded GROQ KEY:", os.getenv("GROQ_API_KEY"))
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


# 🔥 UPDATED SYSTEM PROMPT (Multi-Feature Intelligent Agent)

TOOLS_SYSTEM_PROMPT = f"""
You are an advanced AI Travel Assistant (Year: {CURRENT_YEAR}).

You can:
- Find flights
- Find hotels
- Suggest rental cars
- Show weather forecast
- Check visa requirements
- Analyze travel budget
- Recommend destinations
- Generate itinerary

----------------------------------------------------
CRITICAL TOOL USAGE RULES (STRICT)
----------------------------------------------------

1. If flights are needed → ALWAYS call flights_finder first.
2. If hotels are needed → ALWAYS call hotels_finder.
3. If weather is requested → ALWAYS call weather_finder.
4. If visa information is requested → ALWAYS call visa_checker.
5. If rental cars are requested → ALWAYS call cars_finder.

IMPORTANT:
- NEVER generate weather, flights, hotels, visa or cars manually.
- ALWAYS wait for tool response before generating final answer.
- If a tool returns an error, clearly mention:
  "Live data currently unavailable."

- DO NOT skip tool calls.
- DO NOT generate placeholder information.

----------------------------------------------------
OUTPUT FORMAT (STRICTLY FOLLOW)
----------------------------------------------------

Use section headers with ###:

### Flights
### Hotels
### Rental Cars
### Weather
### Visa Information
### Budget Analysis
### Itinerary

----------------------------------------------------
SECTION FORMAT RULES
----------------------------------------------------

Flights:
1. Airline Name
   - Departure: XXX → Arrival: XXX
   - Duration: XXX
   - Price: $XXX (Economy/Business)
   - Logo: logo_url
   - Booking: url

Hotels:
1. Hotel Name
   - Location: XXX
   - Rating: X.X/5
   - Rate: $XXX per night
   - Total: $XXXX
   - Image: image_url
   - Website: url

Rental Cars:
1. Company
   - Price per day: $XXX
   - Booking: url

Weather:
- City: XXX
- Temperature: XX°C
- Description: XXX

Visa Information:
- Visa Required: Yes/No
- Explanation: Short explanation

Budget Analysis:
- Total Flight Cost: $XXX
- Total Hotel Cost: $XXX
- Total Trip Cost: $XXX
- Budget: $XXX
- Remaining / Exceeded: $XXX

Itinerary:
Day 1:
- Activity 1
- Activity 2
- Activity 3

Day 2:
- Activity 1
- Activity 2
- Activity 3

----------------------------------------------------

Rules:
- Keep clean spacing.
- No emojis.
- No extra commentary.
- No markdown images syntax.
- Only structured readable output.
- Only show sections that were requested.
"""


# 🔥 REGISTER ALL TOOLS
TOOLS = [
    flights_finder,
    hotels_finder,
    weather_finder,
    visa_checker,
    cars_finder
]

EMAILS_SYSTEM_PROMPT = """Your task is to convert structured markdown-like text into a valid HTML email body.

- Do not include a ```html preamble in your response.
- The output should be in proper HTML format, ready to be used as the body of an email.
Here is an example:
<example>
Input:

I want to travel to New York from Madrid from October 1-7. Find me flights and 4-star hotels.

Expected Output:

<!DOCTYPE html>
<html>
<head>
    <title>Flight and Hotel Options</title>
</head>
<body>
    <h2>Flights from Madrid to New York</h2>
    <ol>
        <li>
            <strong>American Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:25 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:25 PM<br>
            <strong>Duration:</strong> 8 hours<br>
            <strong>Aircraft:</strong> Boeing 777<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/AA.png" alt="American Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Iberia</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 12:25 PM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 2:40 PM<br>
            <strong>Duration:</strong> 8 hours 15 minutes<br>
            <strong>Aircraft:</strong> Airbus A330<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/IB.png" alt="Iberia"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Delta Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:00 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:30 PM<br>
            <strong>Duration:</strong> 8 hours 30 minutes<br>
            <strong>Aircraft:</strong> Boeing 767<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $738<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/DL.png" alt="Delta Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
    </ol>

    <h2>4-Star Hotels in New York</h2>
    <ol>
        <li>
            <strong>NobleDen Hotel</strong><br>
            <strong>Description:</strong> Modern, polished hotel offering sleek rooms, some with city-view balconies, plus free Wi-Fi.<br>
            <strong>Location:</strong> Near Washington Square Park, Grand St, and JFK Airport.<br>
            <strong>Rate per Night:</strong> $537<br>
            <strong>Total Rate:</strong> $3,223<br>
            <strong>Rating:</strong> 4.8/5 (656 reviews)<br>
            <strong>Amenities:</strong> Free Wi-Fi, Parking, Air conditioning, Restaurant, Accessible, Business centre, Child-friendly, Smoke-free property<br>
            <img src="https://lh5.googleusercontent.com/p/AF1QipNDUrPJwBhc9ysDhc8LA822H1ZzapAVa-WDJ2d6=s287-w287-h192-n-k-no-v1" alt="NobleDen Hotel"><br>
            <a href="http://www.nobleden.com/">Visit Website</a>
        </li>
        <!-- More hotel entries here -->
    </ol>
</body>
</html>

</example>


"""


class Agent:

    def __init__(self):

        self._tools = {t.name: t for t in TOOLS}

        # ✅ GROQ LLM ONLY
        self._tools_llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
            max_tokens=4096,
        ).bind_tools(TOOLS)

        builder = StateGraph(AgentState)

        builder.add_node("call_tools_llm", self.call_tools_llm)
        builder.add_node("invoke_tools", self.invoke_tools)
        builder.add_node("email_sender", self.email_sender)

        builder.set_entry_point("call_tools_llm")

        builder.add_conditional_edges(
            "call_tools_llm",
            Agent.exists_action,
            {
                "more_tools": "invoke_tools",
                "email_sender": "email_sender",
            },
        )

        builder.add_edge("invoke_tools", "call_tools_llm")
        builder.add_edge("email_sender", END)

        memory = MemorySaver()

        self.graph = builder.compile(
            checkpointer=memory,
            interrupt_before=["email_sender"],
        )

        print(self.graph.get_graph().draw_mermaid())

        # store API key and model preference list
        self._groq_api_key = os.getenv("GROQ_API_KEY")
        # GROQ_MODEL_LIST can be a comma-separated list of preferred models
        self._groq_model_list = [m.strip() for m in os.getenv("GROQ_MODEL_LIST", "llama-3.1-405b-reasoning,llama-3.1-70b-versatile").split(",") if m.strip()]

    def _get_model_candidates(self):
        explicit = os.getenv("GROQ_MODEL")
        if explicit:
            return [explicit] + [m for m in self._groq_model_list if m != explicit]
        return list(self._groq_model_list)

    def _invoke_with_fallback(self, messages, temperature=0.2, bind_tools=False):
        last_exc = None
        for model in self._get_model_candidates():
            try:
                llm = ChatGroq(model=model, groq_api_key=self._groq_api_key, temperature=temperature)
                if bind_tools:
                    llm = llm.bind_tools(TOOLS)
                return llm.invoke(messages)
            except Exception as e:
                last_exc = e
                msg = str(e)
                if "model_decommissioned" in msg or "decommissioned" in msg:
                    print(f"Model {model} decommissioned, trying next model...")
                    continue
                raise
        raise last_exc

    @staticmethod
    def exists_action(state: AgentState):
        result = state["messages"][-1]
        if len(result.tool_calls) == 0:
            return "email_sender"
        return "more_tools"

    def email_sender(self, state: AgentState):
        print("Sending email...")
        email_message = [
            SystemMessage(content=EMAILS_SYSTEM_PROMPT),
            HumanMessage(content=state["messages"][-1].content),
        ]

        email_response = self._invoke_with_fallback(email_message, temperature=0.1, bind_tools=False)

        message = Mail(
            from_email=os.environ["FROM_EMAIL"],
            to_emails=os.environ["TO_EMAIL"],
            subject=os.environ["EMAIL_SUBJECT"],
            html_content=email_response.content,
        )

        try:
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            response = sg.send(message)
            print(response.status_code)
        except Exception as e:
            print("Email Error:", str(e))

    def call_tools_llm(self, state: AgentState):
        messages = state["messages"]
        messages = [SystemMessage(content=TOOLS_SYSTEM_PROMPT)] + messages
        message = self._invoke_with_fallback(messages, temperature=0.2, bind_tools=True)
        return {"messages": [message]}

    def invoke_tools(self, state: AgentState):
        tool_calls = state["messages"][-1].tool_calls
        results = []

        for t in tool_calls:
            print(f"Calling tool: {t}")

            if t["name"] not in self._tools:
                result = "Invalid tool name"
            else:
                result = self._tools[t["name"]].invoke(t["args"])

            results.append(
                ToolMessage(
                    tool_call_id=t["id"],
                    name=t["name"],
                    content=str(result),
                )
            )

        print("Returning tool results to model...")
        return {"messages": results}