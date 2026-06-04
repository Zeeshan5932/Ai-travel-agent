import os
from typing import Optional
import datetime
import serpapi
from langchain.pydantic_v1 import BaseModel, Field

from langchain_core.tools import tool

# from pydantic import BaseModel, Field
today = datetime.date.today()
checkin = today + datetime.timedelta(days=30)
checkout = today + datetime.timedelta(days=40)

class HotelsInput(BaseModel):
    q: str = Field(description='Location of the hotel')
    check_in_date: str = Field(description='Check-in date. The format is YYYY-MM-DD. e.g. 2024-06-22')
    check_out_date: str = Field(description='Check-out date. The format is YYYY-MM-DD. e.g. 2024-06-28')
    sort_by: Optional[str] = Field(8, description='Parameter is used for sorting the results. Default is sort by highest rating')
    adults: Optional[int] = Field(1, description='Number of adults. Default to 1.')
    children: Optional[int] = Field(0, description='Number of children. Default to 0.')
    rooms: Optional[int] = Field(1, description='Number of rooms. Default to 1.')
    hotel_class: Optional[str] = Field(
        None, description='Parameter defines to include only certain hotel class in the results. for example- 2,3,4')


class HotelsInputSchema(BaseModel):
    params: HotelsInput


@tool(args_schema=HotelsInputSchema)
def hotels_finder(params: HotelsInput):
    """
    Find hotels using Google Hotels engine.
    """

    query = {
    "api_key": os.environ.get("SERPAPI_API_KEY"),
    "engine": "google_hotels",
    "hl": "en",
    "gl": "us",
    "q": params.q,
    "check_in_date": checkin.strftime("%Y-%m-%d"),
    "check_out_date": checkout.strftime("%Y-%m-%d"),
    "currency": "USD",
    "adults": params.adults,
    "rooms": params.rooms,
}

    try:
        search = serpapi.search(query)
        data = search.data
        return data.get("properties", [])[:5]

    except Exception as e:
        print("❌ HOTEL TOOL ERROR:", str(e))
        return {"error": "Hotel data unavailable"}
