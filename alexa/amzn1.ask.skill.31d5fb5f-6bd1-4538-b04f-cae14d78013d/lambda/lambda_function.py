# lambda_function.py
import os
import logging

from google import genai
from key import GEMINI_API_KEY

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def call_gemini(prompt: str) -> str:
    """Send the user's prompt to Gemini and return plain text."""
    api_key = GEMINI_API_KEY
    if not api_key:
        logger.error("GEMINI_API_KEY is not set")
        return "Gemini API key is not configured."

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = getattr(response, "text", "") or ""
        text = text.replace("<", " ").replace(">", " ").replace("&", " ").strip()
        if not text:
            return "Gemini did not return any text."
        return text

    except Exception as e:
        logger.exception("Gemini request failed")
        return "I couldn’t reach Gemini."


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speak = "What would you like me to ask Gemini?"
        return handler_input.response_builder.speak(speak).ask(speak).response


class FreeQueryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("FreeQueryIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        intent = handler_input.request_envelope.request.intent
        q_slot = intent.slots.get("q") if intent and intent.slots else None
        user_query = q_slot.value if q_slot and q_slot.value else None

        if not user_query:
            speak = "What should I send to Gemini?"
            return handler_input.response_builder.speak(speak).ask(speak).response

        reply = call_gemini(user_query)

        # Simple heuristic: if short, keep session open
        rb = handler_input.response_builder.speak(reply)
        if len(reply) < 600:
            rb = rb.ask("Would you like to ask Gemini anything else?")
        return rb.response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speak = "Say, ask Gemini followed by your question."
        return handler_input.response_builder.speak(speak).ask(speak).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input)
            or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.speak("Goodbye.").response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception) -> bool:
        return True

    def handle(self, handler_input, exception) -> Response:
        logger.exception("Unhandled error")
        speak = "Sorry, something went wrong."
        return handler_input.response_builder.speak(speak).ask("Try again?").response


sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(FreeQueryIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
