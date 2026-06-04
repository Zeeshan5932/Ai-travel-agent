import os
from serpapi import GoogleSearch
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
    }

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {"error": "SERPAPI_API_KEY is missing. Add it to your .env file."}

    params["api_key"] = api_key

    try:
        search = GoogleSearch(params)
        result = search.get_dict()
        return result.get("organic_results", [])[:3]
    except Exception as e:
        return {"error": f"SerpAPI request failed: {str(e)}"}