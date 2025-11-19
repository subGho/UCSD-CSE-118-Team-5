import os, logging, json, re
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from key import GEMINI_API_KEY

import urllib.request
import urllib.error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
TIMEOUT_SEC = 6  # keep it tight so Alexa can respond under the ~8s total window


def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured."

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {"maxOutputTokens": 350}
    }

    data = json.dumps(payload).encode("utf-8")
    url = f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}"
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            cand = body.get("candidates", [{}])[0]
            parts = cand.get("content", {}).get("parts", [])
            text = ""

            for p in parts:
                if "text" in p:
                    text += p["text"]

            if not text:
                text = "I didn’t receive any content from Gemini."

            return sanitize_for_ssml(text)

    except urllib.error.HTTPError as e:
        logger.error(f"Gemini HTTPError: {e.read().decode('utf-8', errors='ignore')}")
        return "Gemini returned an error."

    except Exception as e:
        logger.exception("Gemini request failed")
        return "I couldn’t reach Gemini."


def sanitize_for_ssml(text: str) -> str:
    text = re.sub(r"[<>&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:7000]


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak = "What would you like me to ask Gemini?"
        return handler_input.response_builder.speak(speak).ask(speak).response


class FreeQueryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("FreeQueryIntent")(handler_input)

    def handle(self, handler_input):
        intent = handler_input.request_envelope.request.intent
        q_slot = intent.slots.get("q") if intent and intent.slots else None
        user_query = q_slot.value if q_slot and q_slot.value else None

        if not user_query:
            speak = "What should I send to Gemini?"
            return handler_input.response_builder.speak(speak).ask(speak).response

        reply = call_gemini(user_query)
        keep_open = len(reply) < 600

        rb = handler_input.response_builder.speak(reply)
        if keep_open:
            rb = rb.ask("Would you like to ask Gemini anything else?")

        return rb.response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        speak = "Tell me what to send to Gemini."
        return handler_input.response_builder.speak(speak).ask(speak).response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak = (
            "Say, ask gemini followed by your question. "
            "For example, ask gemini to write a short poem about space."
        )
        return handler_input.response_builder.speak(speak).ask("What should I send?").response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
            ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input)
            or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)
        )

    def handle(self, handler_input):
        return handler_input.response_builder.speak("Goodbye.").response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.exception("Unhandled error")
        speak = "Sorry, something went wrong."
        return handler_input.response_builder.speak(speak).ask("Try again?").response


sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(FreeQueryIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
