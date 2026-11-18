
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
You are an intelligent customer-support ticket conversation analyst.

Understand the customer's LATEST message using the complete context.

ORIGINAL CUSTOMER COMPLAINT:
{original_complaint or "Not provided yet"}

ADDITIONAL DETAILS ALREADY COLLECTED:
{existing_details or "None"}

PREVIOUS ISSUE SUMMARY:
{existing_summary or "Not available"}

CONVERSATION HISTORY:
{history_text or "No previous conversation."}

LATEST CUSTOMER MESSAGE:
{customer_message}

Choose exactly one action:

1. ADD_DETAIL
   The message provides relevant information about the current issue.
   Extract only the new relevant information.

2. GREETING
   The message is only a greeting or casual social message.

3. UNRELATED
   The message changes to a different topic.

4. COMPLETE
   The customer clearly indicates that they have finished explaining
   the current issue.

5. PAUSE
   The customer explicitly wants to pause or continue later.

6. CANCEL
   The customer explicitly wants to cancel the ticket request.

7. UNCERTAIN
   The meaning is unclear.

IMPORTANT RULES:

- Understand messages in the context of the entire conversation.
- Customers may explain one issue across many messages.
- Do not treat every short message as unrelated.
- Greetings must not be added to ticket details.
- Do not add unrelated questions or casual conversation to ticket details.
- Extract only information genuinely relevant to the current issue.
- Do not invent order numbers, dates, amounts, causes, or other facts.
- Do not mark an issue complete merely because one message is short.
- Only use COMPLETE when the customer clearly indicates they have finished.
- If the customer adds a correction, use the corrected information.
- Keep the summary factual and preserve important details.
- PAUSE and CANCEL messages are workflow instructions, not issue details.
- For GREETING, UNRELATED, PAUSE and CANCEL, return an empty issue_summary.
- If the message is unclear, ask one short relevant clarification question.
- Do not ask for an email address.

Return ONLY one valid JSON object:

{{
    "action": "ADD_DETAIL",
    "confidence": 0.95,
    "relevant_details": "",
    "issue_summary": "",
    "needs_clarification": false,
    "clarification_question": ""
}}
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
    if action in {"GREETING", "UNRELATED", "PAUSE", "CANCEL"}:
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
