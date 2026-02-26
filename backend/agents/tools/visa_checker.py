import os
import serpapi
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
            "api_key": os.getenv("SERPAPI_API_KEY")
        }

        search = serpapi.search(params)
        results = search.data.get("organic_results", [])

        if not results:
            return "Visa information not found."

        return results[:3]

    except Exception as e:
        return f"Error: {str(e)}"