from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import uuid
import markdown

from agents.agent import Agent

app = FastAPI()
agent = Agent()

class TravelRequest(BaseModel):
    query: str

@app.post("/travel")
def get_travel_info(request: TravelRequest):
    thread_id = str(uuid.uuid4())
    messages = [HumanMessage(content=request.query)]
    config = {"configurable": {"thread_id": thread_id}}

    result = agent.graph.invoke({"messages": messages}, config=config)

    raw_markdown = result["messages"][-1].content
    html_output = markdown.markdown(raw_markdown)

    return {
        "response": html_output
    }

