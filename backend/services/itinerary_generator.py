from langchain_openai import ChatOpenAI

def generate_itinerary(destination: str, days: int):
    llm = ChatOpenAI(model="gpt-4o")

    prompt = f"""
    Create a detailed {days}-day travel itinerary for {destination}.
    Include attractions, food, activities.
    """

    response = llm.invoke(prompt)
    return response.content