import json
import logging
import urllib.request
import urllib.error
import urllib.parse

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from key import GEMINI_API_KEY

sb = SkillBuilder()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

# -----------------------------
# Hardcoded text-based calendar
# -----------------------------
CALENDAR_TEXT = """
TODAY
- 10:00 AM – SWE Board Meeting
- 2:00 PM – CSE 118 Lecture
- 3:30 PM – CSE 118 Lab
- 5:00 PM – Study Session

"""

DOOR_API_BASE_URL = "https://deliberative-michell-nonloyal.ngrok-free.dev"
    # you can later move this into an env var if you want

def fetch_door_data(user_id: str = "subhon") -> dict:
    """Call your Flask /weather endpoint and return the JSON as a dict."""
    query = urllib.parse.urlencode({"userId": user_id})
    url = f"{DOOR_API_BASE_URL}/weather?{query}"

    logger.info(f"Fetching door data from: {url}")

    with urllib.request.urlopen(url, timeout=5) as resp:
        body = resp.read().decode("utf-8")
        data = json.loads(body)

    logger.info(f"Door API response: {data}")
    return data

# ---------------------------------------------------------
# Gemini: Summarize Calendar
# ---------------------------------------------------------
def summarize_calendar_with_gemini():
    if not GEMINI_API_KEY:
        logger.error("Gemini API key missing.")
        return "Your schedule summary is unavailable because the API key is missing."

    prompt = (
        "You are an assistant that summarizes schedules. "
        "Given the following day calendar, create a clear, friendly spoken summary "
        "of the main events, commitments, and patterns. Keep it short and natural.\n\n"
        f"{CALENDAR_TEXT}"
    )

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
    }

    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        GEMINI_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        logger.info("Gemini payload: %s", payload)

        # Extract response text
        candidates = payload.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"].strip()

        return "I couldn't summarize your schedule."

    except Exception as e:
        logger.exception("Gemini request failed: %s", e)
        return "I couldn't retrieve your schedule summary due to an error."
        
   


# ---------------------------------------------------------
# Alexa Handlers
# ---------------------------------------------------------

@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input: HandlerInput):
    speak_output = (
        "Welcome, You can say  'summarize my calendar' "
        "or 'check door monitor'. What would you like to do?"
    )
    
    return (
        handler_input.response_builder
        .speak(speak_output)
        .ask("You can say 'summarize my calendar' or 'check door monitor'.")
        .response
    )
    
@sb.request_handler(can_handle_func=is_request_type("GetCalendarSummaryIntent"))
def launch_request_handler(handler_input: HandlerInput):
    summary = summarize_calendar_with_gemini()
    return (
        handler_input.response_builder
        .speak(summary)
        .set_should_end_session(True)
        .response
    )
    
@sb.request_handler(can_handle_func=is_intent_name("DoorStatusIntent"))
def door_status_handler(handler_input: HandlerInput):
    """Respond with the latest door status from MongoDB via your Flask API."""
    try:
        data = fetch_door_data("subhon")  # hard-coded user for now

        door = data.get("doorStatus", "unknown")
        walked = data.get("walkThroughStatus", "unknown")
        temp = data.get("indoorTemp", "unknown")

        if walked == "True":
            walked_phrase = "You recently walked through the door."
        elif walked == "False":
            walked_phrase = "You have not walked through the door yet."
        else:
            walked_phrase = "I'm not sure if you've walked through the door."

        speak_output = (
            f"The door is currently {door}. "
            f"{walked_phrase} "
            f"The indoor temperature is {temp} degrees."
        )

    except Exception as e:
        logger.exception(f"Error in door_status_handler: {e}")
        speak_output = "Sorry, I couldn't get the latest door information."

    return (
        handler_input.response_builder
        .speak(speak_output)
        .set_should_end_session(True)
        .response
    )


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_handler(handler_input):
    speak_output = "This skill summarizes your weekly schedule."
    return (
        handler_input.response_builder
        .speak(speak_output)
        .ask(speak_output)
        .response
    )


@sb.request_handler(
    can_handle_func=lambda h:
        is_intent_name("AMAZON.StopIntent")(h) or
        is_intent_name("AMAZON.CancelIntent")(h)
)
def stop_handler(handler_input):
    return handler_input.response_builder.speak("Goodbye!").set_should_end_session(True).response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
def fallback_handler(handler_input):
    speak_output = "Sorry, I didn't understand. Try opening the schedule again."
    return handler_input.response_builder.speak(speak_output).ask(speak_output).response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_handler(handler_input):
    return handler_input.response_builder.response


@sb.exception_handler(can_handle_func=lambda i, e: True)
def generic_exception_handler(handler_input, exception):
    logger.exception(f"Unhandled exception: {exception}")
    return (
        handler_input.response_builder
        .speak("Sorry, something went wrong.")
        .set_should_end_session(True)
        .response
    )

lambda_handler = sb.lambda_handler()
