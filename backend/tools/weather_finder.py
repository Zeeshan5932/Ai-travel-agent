import os
import requests
from langchain_core.tools import tool


@tool
def get_weather(city: str):
    """
    Get the current weather for a given city using wttr.in API.
    """
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    response = requests.get(url).json()
    
    
    return{
        "city": city,
        "temperature": response["main"]["temp"],
        "description": response["weather"][0]["description"]
    }
    