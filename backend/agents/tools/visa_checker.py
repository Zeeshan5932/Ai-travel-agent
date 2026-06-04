import os
from serpapi import GoogleSearch
from langchain_core.tools import tool

@tool
def visa_checker(nationality: str, destination: str):
    """
    Dynamically check visa requirement using web search.
    """

    try:
        query = f"Do {nationality} passport holders need visa for {destination}?"

        params = {
            "engine": "google",
            "q": query,
        }

        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return {"error": "SERPAPI_API_KEY is missing. Add it to your .env file."}

        params["api_key"] = api_key

        search = GoogleSearch(params)
        results = search.get_dict().get("organic_results", [])

        if not results:
            return "Visa information not found."

        return results[:3]

    except Exception as e:
        return {"error": f"SerpAPI request failed: {str(e)}"}