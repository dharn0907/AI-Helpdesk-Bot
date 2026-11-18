
"""Gemini-powered conversational and conversation-understanding service."""

import json
import re

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    temperature=0.2
)


def extract_response_text(content):
    """Extract text from Gemini response content."""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        return " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
        ).strip()

    return str(content).strip()


def parse_json_response(response_text):
    """Safely parse JSON returned by Gemini."""

    cleaned = response_text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)

        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    return None


def classify_conversation_turn(
    customer_message: str,
    conversation_history: list = None,
    conversation_state: dict = None
):
    """
    Understand the customer's conversational intention
    before running complaint classification.
    """

    if not customer_message or not customer_message.strip():
        raise ValueError("Customer message cannot be empty.")

    history_text = ""

    if conversation_history:
        for item in conversation_history[-12:]:
            role = item.get("role", "user")
            content = item.get("content", "")

            history_text += f"{role.upper()}: {content}\n"

    state_text = json.dumps(
        conversation_state or {},
        ensure_ascii=False,
        default=str
    )

    prompt = f"""
You are the Conversation Understanding Engine of an intelligent
customer-service chatbot.

Your task is to understand what the customer is communicating.

Do not assume that every customer message is a complaint.

A customer may:
- Greet the chatbot.
- Have casual conversations.
- Ask general questions.
- Ask product-related questions.
- Explain a problem.
- Explain a problem gradually over multiple messages.
- Provide additional information about an existing problem.
- Request a human support agent.
- Answer a question asked by the chatbot.

CLASSIFICATION CATEGORIES:

1. SMALL_TALK
   Greetings, thanks, casual conversation and social interaction.

2. GENERAL_QUESTION
   General questions that are not customer complaints.

3. PRODUCT_ENQUIRY
   Questions about products, features, availability and specifications.

4. CUSTOMER_ISSUE
   A new customer problem or complaint.

5. FOLLOW_UP_ISSUE
   Additional information about a previously discussed customer issue.

6. HUMAN_SUPPORT_REQUEST
   The customer explicitly wants to contact a human or raise a ticket.

7. UNCERTAIN
   The intention cannot be determined confidently.

IMPORTANT RULES:

- Interpret the latest message using the conversation history.
- Do not classify a greeting as a complaint.
- Do not classify a normal product enquiry as a complaint.
- Do not treat every message containing words like "order",
  "payment", "account" or "refund" as a complaint.
- A complaint can be distributed across multiple messages.
- If the customer provides an answer to a question asked by the
  chatbot, interpret it using that question and the conversation state.
- Never invent facts about the customer's situation.
- If the customer explicitly requests a human, classify it as
  HUMAN_SUPPORT_REQUEST.
- Do not confuse a general question with a request to create a ticket.
- Use UNCERTAIN when the available information is insufficient.

Return ONLY one valid JSON object in this exact structure:

{{
    "category": "SMALL_TALK",
    "confidence": 0.95,
    "reason": "Brief explanation",
    "issue_summary": "",
    "needs_clarification": false,
    "clarification_question": ""
}}

The category must be one of the seven categories listed above.

CUSTOMER CONVERSATION HISTORY:
{history_text if history_text else "No previous conversation."}

CURRENT CONVERSATION STATE:
{state_text}

LATEST CUSTOMER MESSAGE:
{customer_message}
"""

    response = llm.invoke(prompt)

    response_text = extract_response_text(response.content)

    result = parse_json_response(response_text)

    allowed_categories = {
        "SMALL_TALK",
        "GENERAL_QUESTION",
        "PRODUCT_ENQUIRY",
        "CUSTOMER_ISSUE",
        "FOLLOW_UP_ISSUE",
        "HUMAN_SUPPORT_REQUEST",
        "UNCERTAIN"
    }

    if not isinstance(result, dict):
        return {
            "category": "UNCERTAIN",
            "confidence": 0.0,
            "reason": "Unable to understand the conversation.",
            "issue_summary": "",
            "needs_clarification": True,
            "clarification_question": (
                "Could you please explain what you need help with?"
            )
        }

    category = result.get("category")

    if category not in allowed_categories:
        category = "UNCERTAIN"

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))

    return {
        "category": category,
        "confidence": round(confidence, 4),
        "reason": str(result.get("reason", "")),
        "issue_summary": str(result.get("issue_summary", "")),
        "needs_clarification": bool(
            result.get("needs_clarification", False)
        ),
        "clarification_question": str(
            result.get("clarification_question", "")
        )
    }


def generate_llm_response(
    customer_message: str,
    intent: str = "general_enquiry",
    context: str = "",
    conversation_history: list = None
) -> str:
    """Generate natural conversational and customer-support responses."""

    history_text = ""

    if conversation_history:
        for message in conversation_history[-10:]:
            role = message.get("role", "user")
            content = message.get("content", "")

            history_text += f"{role.upper()}: {content}\n"

    prompt = f"""
You are a friendly, intelligent and natural customer-service chatbot.

Your primary goal is to have a helpful conversation with the customer.

You should behave like a normal human-friendly chatbot, not like a
ticket-processing machine.

CONVERSATIONAL BEHAVIOUR:

1. Respond naturally to greetings and casual conversations.
2. Answer general questions normally.
3. Handle product enquiries conversationally.
4. Understand the customer's previous messages.
5. Do not ask customers to repeat information they have already provided.
6. Do not turn every conversation into a complaint.
7. Do not create or claim to create tickets yourself.
8. Do not claim that an order, payment, refund or account has been verified.
9. Never invent company policies or customer account information.
10. When a genuine problem requires investigation, explain that
    human support can assist.
11. Ask only relevant follow-up questions.
12. Keep responses friendly, clear and concise.

CUSTOMER MESSAGE:
{customer_message}

CONVERSATION HISTORY:
{history_text if history_text else "No previous conversation."}

COMPLAINT CATEGORY:
{intent}

RETRIEVED SUPPORT KNOWLEDGE:
{context if context else "No relevant support information was retrieved."}

Generate the most appropriate conversational response.
"""

    response = llm.invoke(prompt)

    return extract_response_text(response.content)
