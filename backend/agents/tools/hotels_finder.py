import os
from typing import Optional
from typing import Union
import datetime
from pydantic import BaseModel, Field

from langchain_core.tools import tool
from serpapi import GoogleSearch
today = datetime.date.today()
checkin = today + datetime.timedelta(days=30)
checkout = today + datetime.timedelta(days=40)

class HotelsInput(BaseModel):
    q: str = Field(description='Location of the hotel')
    check_in_date: str = Field(description='Check-in date. The format is YYYY-MM-DD. e.g. 2024-06-22')
    check_out_date: str = Field(description='Check-out date. The format is YYYY-MM-DD. e.g. 2024-06-28')
    sort_by: Optional[Union[str, int]] = Field(8, description='Parameter is used for sorting the results. Default is sort by highest rating')
    adults: Optional[int] = Field(1, description='Number of adults. Default to 1.')
    children: Optional[int] = Field(0, description='Number of children. Default to 0.')
    rooms: Optional[int] = Field(1, description='Number of rooms. Default to 1.')
    hotel_class: Optional[str] = Field(
        None, description='Parameter defines to include only certain hotel class in the results. for example- 2,3,4')


class HotelsInputSchema(BaseModel):
    params: HotelsInput


def _first_non_empty(*values):
    for value in values:
        if value not in (None, "", [], {}, ()):
            return value
    return None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def simplify_hotels_response(raw_results):
    if isinstance(raw_results, dict):
        error_message = raw_results.get("error") or raw_results.get("error_message")
        if error_message:
            return {
                "status": "error",
                "message": str(error_message),
                "data": [],
            }

    properties = []

    if isinstance(raw_results, dict):
        properties = raw_results.get("properties") or raw_results.get("hotels_results") or raw_results.get("hotels") or []
    elif isinstance(raw_results, list):
        properties = raw_results

    if not properties:
        return {
            "status": "no_results",
            "message": "No hotels found for the requested search.",
            "data": [],
        }

    simplified = []
    for hotel in properties[:5]:
        if not isinstance(hotel, dict):
            continue

        amenities = hotel.get("amenities") or hotel.get("amenities_list") or []
        if isinstance(amenities, str):
            amenities = [amenities]

        simplified.append(
            {
                "name": _first_non_empty(hotel.get("name"), hotel.get("title")),
                "rating": _first_non_empty(hotel.get("rating"), hotel.get("overall_rating")),
                "reviews": _first_non_empty(hotel.get("reviews"), hotel.get("reviews_count"), hotel.get("total_reviews")),
                "price": _first_non_empty(hotel.get("price"), hotel.get("rate_per_night"), hotel.get("price_per_night")),
                "total_price": _first_non_empty(hotel.get("total_price"), hotel.get("total_rate"), hotel.get("price_total")),
                "hotel_class": _first_non_empty(hotel.get("hotel_class"), hotel.get("class")),
                "location": _first_non_empty(hotel.get("address"), hotel.get("location"), hotel.get("nearby_place"), hotel.get("neighborhood")),
                "amenities": amenities[:5],
                "booking_link": _first_non_empty(hotel.get("booking_link"), hotel.get("link"), hotel.get("url"), hotel.get("website")),
            }
        )

    if not simplified:
        return {
            "status": "no_results",
            "message": "No hotels found for the requested search.",
            "data": [],
        }

    return {
        "status": "success",
        "message": f"Found {len(simplified)} hotel options.",
        "data": simplified,
    }


@tool(args_schema=HotelsInputSchema)
def hotels_finder(params: HotelsInput):
    """
    Find hotels using Google Hotels engine.
    """

    query = {
    "engine": "google_hotels",
    "hl": "en",
    "gl": "us",
    "q": params.q,
    "check_in_date": params.check_in_date or checkin.strftime("%Y-%m-%d"),
    "check_out_date": params.check_out_date or checkout.strftime("%Y-%m-%d"),
    "currency": "USD",
    "adults": params.adults,
    "rooms": params.rooms,
}

    check_in_value = _parse_date(query["check_in_date"])
    check_out_value = _parse_date(query["check_out_date"])
    today_value = datetime.date.today()

    if check_in_value is None or check_out_value is None:
        return {
            "status": "error",
            "message": "Invalid travel date format. Use YYYY-MM-DD.",
            "data": [],
        }

    if check_in_value < today_value or check_out_value < today_value:
        return {
            "status": "error",
            "message": "Travel dates are in the past. Please provide future dates.",
            "data": [],
        }

    if check_out_value < check_in_value:
        return {
            "status": "error",
            "message": "Check-out date must be after the check-in date.",
            "data": [],
        }

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "message": "SERPAPI_API_KEY is missing. Add it to your .env file.",
            "data": [],
        }

    sort_by_value = params.sort_by
    if sort_by_value not in (None, ""):
        query["sort_by"] = str(sort_by_value)

    query["api_key"] = api_key

    try:
        search = GoogleSearch(query)
        raw_results = search.get_dict()
        return simplify_hotels_response(raw_results)

    except Exception as e:
        return {
            "status": "error",
            "message": f"SerpAPI request failed: {str(e)}",
            "data": [],
        }
