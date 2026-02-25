def analyze_budget(total_flight_cost, total_hotel_cost, budget):
    total = total_flight_cost + total_hotel_cost

    if total > budget:
        return f"Trip exceeds budget by ${total - budget}"
    return f"Trip is within budget. Remaining: ${budget - total}"