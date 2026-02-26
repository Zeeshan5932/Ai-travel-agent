import os
import requests
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class WeatherInput(BaseModel):
    city: str = Field(description="City name")


@tool(args_schema=WeatherInput)
def weather_finder(city: str):
    """
    Get current weather for a city.
    """

    api_key = os.getenv("WEATHER_API_KEY")

    if not api_key:
        return {"error": "WEATHER_API_KEY not found in environment"}

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        # 🔥 SAFE CHECK
        if "main" not in data:
            return {"error": data.get("message", "Weather data not available")}

        return {
            "city": city,
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"]
        }

    except Exception as e:
        return {"error": str(e)}