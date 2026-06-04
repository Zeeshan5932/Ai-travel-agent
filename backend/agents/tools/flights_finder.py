# import os
# from typing import Optional

# # from pydantic import BaseModel, Field
# from langchain.pydantic_v1 import BaseModel, Field
# from langchain_core.tools import tool


# class FlightsInput(BaseModel):
#     departure_airport: Optional[str] = Field(description='Departure airport code (IATA)')
#     arrival_airport: Optional[str] = Field(description='Arrival airport code (IATA)')
#     outbound_date: Optional[str] = Field(description='Parameter defines the outbound date. The format is YYYY-MM-DD. e.g. 2024-06-22')
#     return_date: Optional[str] = Field(description='Parameter defines the return date. The format is YYYY-MM-DD. e.g. 2024-06-28')
#     adults: Optional[int] = Field(1, description='Parameter defines the number of adults. Default to 1.')
#     children: Optional[int] = Field(0, description='Parameter defines the number of children. Default to 0.')
#     infants_in_seat: Optional[int] = Field(0, description='Parameter defines the number of infants in seat. Default to 0.')
#     infants_on_lap: Optional[int] = Field(0, description='Parameter defines the number of infants on lap. Default to 0.')


# class FlightsInputSchema(BaseModel):
#     params: FlightsInput


# @tool(args_schema=FlightsInputSchema)
# def flights_finder(params: FlightsInput):
#     '''
#     Find flights using the Google Flights engine.

#     Returns:
#         dict: Flight search results.
#     '''

#     params = {
#         'api_key': os.environ.get('SERPAPI_API_KEY'),
#         'engine': 'google_flights',
#         'hl': 'en',
#         'gl': 'us',
#         'departure_id': params.departure_airport,
#         'arrival_id': params.arrival_airport,
#         'outbound_date': params.outbound_date,
#         'return_date': params.return_date,
#         'currency': 'USD',
#         'adults': params.adults,
#         'infants_in_seat': params.infants_in_seat,
#         'stops': '1',
#         'infants_on_lap': params.infants_on_lap,
#         'children': params.children
#     }

#     try:
#         # results = search.data['best_flights']
#         results = search.data.get('best_flights', [])
#     except Exception as e:
#         results = str(e)
#     return results


import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import datetime
from serpapi import GoogleSearch

today = datetime.date.today()
default_outbound = today + datetime.timedelta(days=30)
default_return = today + datetime.timedelta(days=40)


class FlightsInput(BaseModel):
    departure_airport: Optional[str] = Field(
        description="Departure airport code (IATA)"
    )
    arrival_airport: Optional[str] = Field(
        description="Arrival airport code (IATA)"
    )
    outbound_date: Optional[str] = Field(
        description="Outbound date (YYYY-MM-DD)"
    )
    return_date: Optional[str] = Field(
        description="Return date (YYYY-MM-DD)"
    )
    adults: Optional[int] = Field(1)
    children: Optional[int] = Field(0)
    infants_in_seat: Optional[int] = Field(0)
    infants_on_lap: Optional[int] = Field(0)


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


def simplify_flights_response(raw_results):
    if isinstance(raw_results, dict):
        error_message = raw_results.get("error") or raw_results.get("error_message")
        if error_message:
            return {
                "status": "error",
                "message": str(error_message),
                "data": [],
            }

    flights = []

    if isinstance(raw_results, dict):
        flights = raw_results.get("best_flights") or raw_results.get("other_flights") or raw_results.get("flights") or []
    elif isinstance(raw_results, list):
        flights = raw_results

    if not flights:
        return {
            "status": "no_results",
            "message": "No flights found for the requested search.",
            "data": [],
        }

    simplified = []
    for flight in flights[:5]:
        if not isinstance(flight, dict):
            continue

        segments = flight.get("flights") or flight.get("segments") or []
        first_segment = segments[0] if segments else {}

        airline = _first_non_empty(
            flight.get("airline"),
            first_segment.get("airline"),
            first_segment.get("airline_name"),
        )
        flight_number = _first_non_empty(
            flight.get("flight_number"),
            first_segment.get("flight_number"),
            first_segment.get("flight"),
        )
        departure_airport = _first_non_empty(
            flight.get("departure_airport"),
            first_segment.get("departure_airport"),
            first_segment.get("departure_id"),
            first_segment.get("departure_airport_name"),
        )
        arrival_airport = _first_non_empty(
            flight.get("arrival_airport"),
            first_segment.get("arrival_airport"),
            first_segment.get("arrival_id"),
            first_segment.get("arrival_airport_name"),
        )
        departure_time = _first_non_empty(
            flight.get("departure_time"),
            first_segment.get("departure_time"),
            first_segment.get("departure_airport_time"),
        )
        arrival_time = _first_non_empty(
            flight.get("arrival_time"),
            first_segment.get("arrival_time"),
            first_segment.get("arrival_airport_time"),
        )
        duration = _first_non_empty(flight.get("duration"), first_segment.get("duration"))
        stops = _first_non_empty(flight.get("stops"), flight.get("layovers_count"), len(segments) - 1 if segments else None)
        price = _first_non_empty(flight.get("price"), flight.get("total_price"), flight.get("price_usd"))
        booking_link = _first_non_empty(
            flight.get("booking_link"),
            flight.get("link"),
            flight.get("booking_url"),
        )

        simplified.append(
            {
                "airline": airline,
                "flight_number": flight_number,
                "departure_airport": departure_airport,
                "arrival_airport": arrival_airport,
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "duration": duration,
                "stops": stops,
                "price": price,
                "booking_link": booking_link,
            }
        )

    if not simplified:
        return {
            "status": "no_results",
            "message": "No flights found for the requested search.",
            "data": [],
        }

    return {
        "status": "success",
        "message": f"Found {len(simplified)} flight options.",
        "data": simplified,
    }


@tool(args_schema=FlightsInput)
def flights_finder(
    departure_airport: str,
    arrival_airport: str,
    outbound_date: str,
    return_date: str,
    adults: int = 1,
    children: int = 0,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
):
    """
    Find flights using Google Flights engine.
    """
    outbound_str = outbound_date or default_outbound.strftime("%Y-%m-%d")
    return_str = return_date or default_return.strftime("%Y-%m-%d")

    outbound_date_value = _parse_date(outbound_str)
    return_date_value = _parse_date(return_str)
    today_value = datetime.date.today()

    if outbound_date_value is None or return_date_value is None:
        return {
            "status": "error",
            "message": "Invalid travel date format. Use YYYY-MM-DD.",
            "data": [],
        }

    if outbound_date_value < today_value or return_date_value < today_value:
        return {
            "status": "error",
            "message": "Travel dates are in the past. Please provide future dates.",
            "data": [],
        }

    if return_date_value < outbound_date_value:
        return {
            "status": "error",
            "message": "Return date must be after the outbound date.",
            "data": [],
        }

    params = {
        "engine": "google_flights",
        "hl": "en",
        "gl": "us",
        "departure_id": departure_airport,
        "arrival_id": arrival_airport,
        "outbound_date": outbound_str,
        "return_date": return_str,
        "currency": "USD",
        "adults": adults,
        "children": children,
        "infants_in_seat": infants_in_seat,
        "infants_on_lap": infants_on_lap,
    }

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "message": "SERPAPI_API_KEY is missing. Add it to your .env file.",
            "data": [],
        }

    params["api_key"] = api_key

    try:
        search = GoogleSearch(params)
        raw_results = search.get_dict()
        return simplify_flights_response(raw_results)
    except Exception as e:
        return {
            "status": "error",
            "message": f"SerpAPI request failed: {str(e)}",
            "data": [],
        }