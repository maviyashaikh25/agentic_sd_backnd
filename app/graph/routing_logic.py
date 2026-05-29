from app.chatbot.intent_classifier import classify_intent


def route_intent(state):

    user_input = state["user_input"]

    intent = classify_intent(user_input)

    return intent