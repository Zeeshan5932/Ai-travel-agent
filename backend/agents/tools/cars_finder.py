import os
import serpapi
from langchain_core.tools import tool

@tool
def cars_finder(location: str, pickup_date: str, dropoff_date: str):
    """
    Search for rental cars in a given location between pickup and dropoff dates.

    Returns a list of the top 3 organic search results from Google.
    """
    params = {
        "engine": "google",
        "q": f"car rental in {location}",
        "api_key": os.getenv("SERPAPI_API_KEY")
    }

    search = serpapi.search(params)
    return search.data.get("organic_results", [])[:3]