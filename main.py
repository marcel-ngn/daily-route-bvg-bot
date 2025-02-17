import requests
import datetime

# Function to safely parse time, adding today's date if needed
def parse_time(time_str):
    try:
        # If time is in "HH:MM" format, add today's date
        if len(time_str) == 5 and ":" in time_str:
            today_date = datetime.datetime.today().date()
            time_str = f"{today_date}T{time_str}:00"  # Add seconds for valid ISO format
        return datetime.datetime.fromisoformat(time_str)
    except (ValueError, TypeError):
        return None  # Return None if invalid or unparseable

# Set departure and destination station IDs
departure_station = "Prenzlauer Prom./Kissingenstr. (Berlin)"
destination_station = "S Adlershof (Berlin)"

departure_id = "900130015"
destination_id = "900193002"


# API URL with real-time departure
url = f"https://v6.bvg.transport.rest/journeys?from={departure_id}&to={destination_id}&departure=now&results=3"

# Make the request to the API
response = requests.get(url)
journeys = response.json().get("journeys", [])

# Parse the journeys to format the information
messages = []

for journey in journeys:
    journey_steps = []
    
    # Extract departure and arrival times for total duration calculation
    first_leg_departure = None
    last_leg_arrival = None
    
    for i, leg in enumerate(journey["legs"]):
        origin = leg["origin"]["name"]
        destination = leg["destination"]["name"]

        # Check if line information exists
        line_name = leg["line"]["name"] if "line" in leg else "Unbekannt"
        
        # Handle missing direction (default to "Unbekannt" if missing)
        direction = leg.get("direction", "Unbekannt")

        # Format departure & arrival times (Handle None or invalid date)
        departure_time = leg.get("departure")
        arrival_time = leg.get("arrival")

        if departure_time:
            departure_time_obj = parse_time(departure_time)
            departure_time = departure_time_obj.strftime("%H:%M") if departure_time_obj else "Unbekannt"
            if not first_leg_departure:  # First leg departure time
                first_leg_departure = departure_time_obj
        else:
            departure_time = "Unbekannt"

        if arrival_time:
            arrival_time_obj = parse_time(arrival_time)
            arrival_time = arrival_time_obj.strftime("%H:%M") if arrival_time_obj else "Unbekannt"
            last_leg_arrival = arrival_time_obj  # Last leg arrival time
        else:
            arrival_time = "Unbekannt"

        # Platform information
        departure_platform = leg.get("departurePlatform", "Unbekannt")
        arrival_platform = leg.get("arrivalPlatform", "Unbekannt")

        # Delay handling
        departure_delay = (leg.get("departureDelay") or 0) // 60
        arrival_delay = (leg.get("arrivalDelay") or 0) // 60
        delay_message = ""
        if departure_delay > 0 or arrival_delay > 0:
            delay_message = f"🚨 Verspätung: Abfahrt {departure_delay} min, Ankunft {arrival_delay} min"

        # Remarks (hints, warnings)
        remarks_list = [remark["text"] for remark in leg.get("remarks", []) if remark.get("text")]
        remarks_text = "\n   ⚠️ " + "\n   ⚠️ ".join(remarks_list) if remarks_list else ""

        # Step message
        step_message = (
            f"Schritt {i+1}:\n"
            f"🚉 Start: {origin} um {departure_time}\n"
            f"📍 Linie: {line_name} Richtung {direction}\n"
            f"🚆 Ziel: {destination} um {arrival_time}\n"
            f"{delay_message}\n"
            f"{remarks_text}"
        )
        journey_steps.append(step_message)

        # Indicate train changes
        if i < len(journey["legs"]) - 1:
            journey_steps.append("🔄 ++ Umsteigen nötig ++\n")

    # Calculate total journey duration
    if first_leg_departure and last_leg_arrival:
        journey_duration = last_leg_arrival - first_leg_departure
        total_duration = str(journey_duration).split(".")[0]  # Remove microseconds
        duration_message = f"🕐 Gesamtreisedauer: {total_duration}"
        departure_time_final = first_leg_departure.strftime("%H:%M")
        arrival_time_final = last_leg_arrival.strftime("%H:%M")
        # Add the full travel details including departure and arrival time
        journey_header = f"🚆 Reiseplan nach {destination_station}:\n" \
                         f"🚉 Abfahrt: {departure_time_final} - 🚆 Ankunft: {arrival_time_final}\n"
    else:
        duration_message = "🕐 Gesamtreisedauer: Unbekannt"
        journey_header = f"🚆 Reiseplan nach {destination_station}:\n" \
                         f"🚉 Abfahrt: Unbekannt - 🚆 Ankunft: Unbekannt\n"

    # Combine all steps into a full journey message
    full_journey_message = f"{journey_header}{duration_message}\n\n" + "\n\n".join(journey_steps)
    messages.append(f"\n{full_journey_message}")

    # Add a line break after each journey
    messages.append("================================")  # Line break for readability

# Combine all messages
final_message = "\n\n".join(messages)

# Send via ntfy
ntfy_url = "https://ntfy.sh/m-ngn-testing-2255"  # Replace with your actual ntfy topic
response = requests.post(ntfy_url, data=final_message.encode("utf-8"))

# Check if notification was sent
if response.status_code == 200:
    print("✅ Notification sent!")
else:
    print(f"❌ Failed to send notification. Status code: {response.status_code}")
