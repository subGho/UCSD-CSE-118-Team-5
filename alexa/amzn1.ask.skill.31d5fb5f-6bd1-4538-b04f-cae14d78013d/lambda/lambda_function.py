import json
import logging
import urllib.request
import urllib.error

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
    summary = summarize_calendar_with_gemini()
    return (
        handler_input.response_builder
        .speak(summary)
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
