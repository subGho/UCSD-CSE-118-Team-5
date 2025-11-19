# lambda_function.py
import os, logging, json, re
import GEMINI_API_KEY from key
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from google import genai

import urllib.request
import urllib.error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
TIMEOUT_SEC = 6  # keep it tight so Alexa can respond under the ~8s total window

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured."

    
    # try:
        # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    client = genai.Client()
    
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Explain how AI works in a few words"
    )
    return response.text
       
    # except urllib.error.HTTPError as e:
    #     logger.error(f"Gemini HTTPError: {e.read().decode('utf-8', errors='ignore')}")
    #     return "Gemini returned an error."
    # except Exception as e:
    #     logger.exception("Gemini request failed")
    #     return "I couldn’t reach Gemini."

def sanitize_for_ssml(text: str) -> str:
    # Remove potentially problematic characters for SSML,
    # collapse whitespace, and trim to a safe length (~7000 chars)
    text = re.sub(r"[<>&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Alexa response length hard limit is below 8000 chars; stay conservative:
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

        # Call Gemini
        reply = call_gemini(user_query)
        # If reply is short, keep mic open for follow ups; otherwise, end
        keep_open = len(reply) < 600  # heuristic
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
        speak = "Say, ask gemini followed by your question. For example, ask gemini to write a short poem about space."
        return handler_input.response_builder.speak(speak).ask("What should I send?").response

class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))
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