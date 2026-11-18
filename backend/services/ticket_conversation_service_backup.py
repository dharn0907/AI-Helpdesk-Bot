
from services.llm_service import (
    llm,
    extract_response_text,
    parse_json_response,
)


def interpret_ticket_message(
    customer_message: str,
    pending_ticket: dict,
    conversation_history: list = None,
) -> dict:
    """
    Understand a customer's latest message during ticket collection.

    Gemini interprets the message and extracts relevant details.
    The application controls the ticket workflow.
    """

    original_complaint = pending_ticket.get("original_complaint", "")
    existing_details = pending_ticket.get("additional_details", "")
    existing_summary = pending_ticket.get("issue_summary", "")

    history_text = ""

    if conversation_history:
        for message in conversation_history[-10:]:
            role = message.get("role", "user")
            content = message.get("content", "")
            history_text += f"{role.upper()}: {content}\n"

    prompt = f"""
You are an expert customer-support conversation analyst.

Understand the customer's latest message naturally using the complete
conversation. Customers should feel heard, not processed through a form.

ORIGINAL CUSTOMER COMPLAINT:
{original_complaint or "Not provided yet"}

ADDITIONAL DETAILS ALREADY COLLECTED:
{existing_details or "None"}

CURRENT ISSUE SUMMARY:
{existing_summary or "Not available"}

PREVIOUS CONVERSATION:
{history_text or "No previous conversation."}

LATEST CUSTOMER MESSAGE:
{customer_message}

Choose exactly ONE action:

ADD_DETAIL: New information, an answer to a previous question,
or a correction related to the current issue.

GREETING: Only a greeting or casual social message.

SIDE_QUESTION: ANY question or temporary topic change that is
not intended to add information to the current support issue.
This includes general knowledge, people, sports, technology,
education, entertainment, current affairs, and questions about
the assistant or support process.
Examples: "Who are you?", "Who is Lionel Messi?",
"What is machine learning?", "What is the capital of Japan?"

UNRELATED: Use only when the customer clearly wants to permanently
abandon the current conversation and move to another task, rather
than asking a temporary question. Do not use UNRELATED merely
because the question is about a different subject.

COMPLETE: The customer clearly says they have finished explaining.

PAUSE: The customer wants to continue later.

CANCEL: The customer wants to stop or does not want to raise a ticket.
Recognize natural expressions such as "I don't need a ticket",
"I don't want to raise a ticket", "forget it", "never mind",
"don't create a ticket", and "leave it".

UNCERTAIN: The meaning is genuinely ambiguous.

CONVERSATION INTELLIGENCE:

1. Interpret short answers using the previous conversation.
2. Remember information already provided.
3. Never ask the customer to repeat answered questions.
4. Recognize corrections and use the latest corrected information.
5. Extract only new information relevant to the current issue.
6. Do not duplicate existing details.
7. Preserve error messages, devices, timing, frequency, impact,
   and troubleshooting steps when provided.
8. Never invent missing information or causes.
9. Do not classify relevant short answers as unrelated.
10. Do not mark an issue complete just because a message is short.
11. Ask one specific clarification question only when necessary.
12. Avoid generic questions when a more relevant question is possible.
13. PAUSE and CANCEL are workflow instructions, not issue details.
14. Recognize indirect but clear cancellation requests. Do not require
    the customer to use the exact word CANCEL.
15. A simple question about your identity or the support process is
    SIDE_QUESTION, not UNRELATED.
16. SIDE_QUESTION must not modify the complaint, details, or summary.
17. Do not interpret a customer's question as cancellation unless
    they clearly express that they want to stop the ticket request.

SUMMARY:

- Keep the summary factual, concise and understandable.
- Include the original complaint and all known relevant details.
- Preserve customer corrections.
- Never introduce assumptions.
- For GREETING, UNRELATED, PAUSE and CANCEL, return an empty summary.
- For ADD_DETAIL and COMPLETE, use all known relevant information.

Return ONLY valid JSON in this exact structure:

{{
    "action": "ADD_DETAIL",
    "confidence": 0.95,
    "relevant_details": "Only new relevant information",
    "issue_summary": "Updated factual issue summary",
    "needs_clarification": false,
    "clarification_question": ""
}}

For UNCERTAIN, provide one specific clarification question.
Do not ask for an email address.
"""

    try:
        response = llm.invoke(prompt)
        response_text = extract_response_text(response.content)
        result = parse_json_response(response_text)
    except Exception:
        result = None

    allowed_actions = {
        "ADD_DETAIL",
        "GREETING",
        "SIDE_QUESTION",
        "UNRELATED",
        "COMPLETE",
        "PAUSE",
        "CANCEL",
        "UNCERTAIN",
    }

    if not isinstance(result, dict):
        return {
            "action": "UNCERTAIN",
            "confidence": 0.0,
            "relevant_details": "",
            "issue_summary": existing_summary,
            "needs_clarification": True,
            "clarification_question": (
                "Could you clarify whether this information relates "
                "to the issue you are reporting?"
            ),
        }

    action = str(result.get("action", "UNCERTAIN")).upper()

    if action not in allowed_actions:
        action = "UNCERTAIN"

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))

    relevant_details = str(
        result.get("relevant_details", "")
    ).strip()

    issue_summary = str(
        result.get("issue_summary", "")
    ).strip()

    # Never allow workflow or casual messages to change the issue summary.
    if action in {
        "GREETING", "SIDE_QUESTION", "UNRELATED", "PAUSE", "CANCEL"
    }:
        relevant_details = ""
        issue_summary = ""

    return {
        "action": action,
        "confidence": round(confidence, 4),
        "relevant_details": relevant_details,
        "issue_summary": issue_summary,
        "needs_clarification": bool(
            result.get("needs_clarification", False)
        ),
        "clarification_question": str(
            result.get("clarification_question", "")
        ).strip(),
    }
