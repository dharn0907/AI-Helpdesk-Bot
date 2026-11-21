import json

from services.llm_service import (
    llm,
    extract_response_text,
    parse_json_response,
)


def interpret_ticket_message(
    customer_message: str,
    pending_ticket: dict,
    conversation_history: list = None,
    company_config: dict = None,
) -> dict:
    """
    Analyse the customer's support conversation.

    Gemini identifies relevant details, missing information,
    contradictions, corrections and the next useful question using
    an adaptive, domain-aware investigation strategy.

    The backend remains responsible for ticket workflow.
    """

    original_complaint = pending_ticket.get("original_complaint", "")
    existing_details = pending_ticket.get("additional_details", "")
    existing_summary = pending_ticket.get("issue_summary", "")
    company_context = json.dumps(
        company_config or {},
        ensure_ascii=False,
        default=str,
    )

    history_text = ""

    if conversation_history:
        for message in conversation_history[-12:]:
            role = message.get("role", "user")
            content = message.get("content", "")
            history_text += f"{role.upper()}: {content}\n"

    prompt = f"""
You are an expert customer-support investigation analyst.

Your job is to understand the customer's issue like an experienced
human support representative.

Analyse the COMPLETE conversation, not just the latest message.

ORIGINAL COMPLAINT:
{original_complaint or "Not provided"}

DETAILS ALREADY COLLECTED:
{existing_details or "None"}

CURRENT ISSUE SUMMARY:
{existing_summary or "Not available"}

ACTIVE COMPANY / BOT CONTEXT (authoritative domain and support scope):
{company_context if company_context != "{}" else "No company configuration supplied."}

PENDING CONTRADICTIONS:
{pending_ticket.get("pending_contradictions", [])}

INFORMATION AWAITING CLARIFICATION:
{pending_ticket.get("pending_correction", "")}

QUESTIONS ALREADY ASKED:
{pending_ticket.get("asked_questions", []) or "None"}

CONVERSATION HISTORY:
{history_text or "No previous conversation"}

LATEST CUSTOMER MESSAGE:
{customer_message}

FIRST: CLASSIFY THE CUSTOMER'S MESSAGE.

Choose exactly one action:

ADD_DETAIL:
The customer provides new relevant information, answers a question,
or explicitly corrects earlier information.

GREETING:
Only a greeting or casual social message.

SIDE_QUESTION:
The customer temporarily asks something unrelated to the support issue.

UNRELATED:
The customer clearly wants to abandon the current topic and move
to a different task. Do not use this for temporary questions.

COMPLETE:
The customer clearly indicates they have finished explaining the issue.

PAUSE:
The customer wants to continue later.

CANCEL:
The customer clearly does not want to proceed with the support request.

UNCERTAIN:
The meaning is genuinely unclear.

SECOND: INVESTIGATE THE INFORMATION.

ADAPTIVE INVESTIGATION STRATEGY (IMPORTANT):
- Investigate in the context of the configured company's actual business,
  products, services, systems, and support scope. Do not assume any industry
  unless the company configuration supports it.
- First understand what the customer is experiencing, what they were trying
  to do, and what outcome they expected. If the issue is vague, clarify it
  before asking for identifiers or technical details.
- Build a complaint-specific investigation plan internally. Choose only the
  facts that are diagnostically useful for THIS issue. Do not use a fixed
  checklist or ask every example below.
- Depending on the issue, relevant details may include the affected product,
  service, feature, process or account area; expected versus actual result;
  symptoms or error text; when it began; frequency; steps that trigger it;
  device, browser, app version, location or environment; impact or urgency;
  previous attempts and their results; or a necessary non-sensitive reference
  and date. These are examples, not universal mandatory fields.
- For technical/service issues, prioritize reproduction steps, actual and
  expected behavior, error messages, timing, environment, and attempts when
  relevant. For billing/transaction issues, collect only necessary non-secret
  reference/date and reported outcome. For physical products, ask about the
  product, symptoms, condition and relevant context. Adapt to other domains.
- Use company configuration and retrieved support knowledge to avoid asking
  irrelevant questions or facts the company already has. Never claim a system
  was checked unless a backend/tool result confirms it.
- Ask one highest-value next question that helps diagnose, reproduce, verify,
  or route the issue. Keep it conversational, not a questionnaire.
- If the customer does not know, refuses, or cannot provide a detail, record
  that accurately and move to another useful question; do not ask again.
- Stop when the summary is actionable for a support team. Do not prolong the
  conversation to collect arbitrary amounts of information; set
  information_complete true when sufficient.
- Never request passwords, OTPs, full card/bank details, API keys, recovery
  codes, or other authentication secrets.

0. NEGATIVE ANSWERS AND UNAVAILABLE INFORMATION:

   - A negative response to the bot's previous question is still a
     valid answer.
   - For example, if the bot asks for a screenshot and the customer
     says "I don't have the screenshot", classify it as ADD_DETAIL.
   - The same applies to "I don't know", "I can't access it",
     "I don't remember" and "I cannot provide that", when they
     answer a previous question.
   - Record what the customer cannot provide in relevant_details
     and update the issue_summary accordingly.
   - Do not classify these responses as UNCERTAIN merely because
     the requested information is unavailable.
   - Do not ask for the same unavailable information again.
   - Continue by asking one different, useful question if needed.
   - Never invent the missing information.

STRICT INVESTIGATION RULES ? OVERRIDE GENERIC BEHAVIOUR:

1. If the latest customer message directly answers the previous
   assistant question, ALWAYS classify it as ADD_DETAIL.
   Never ask whether that answer is relevant.

2. Answers such as "yes", "no", "I already tried that",
   "it did not work", "I don't know", "that's all", and
   corrections must be interpreted using the conversation history.

3. NEVER offer, suggest, or ask whether the customer wants
   a human agent during normal information collection.
   Continue investigating with one relevant question.
   Only initiate human handoff when the customer explicitly
   requests a human agent or explicitly asks to create a ticket.

4. If the customer says they do not want a human and want
   further investigation, respect that and continue investigating.
   Do not ask about human support again.

5. Before generating next_question, compare it against ALL
   questions already asked and answered in the conversation.
   Never ask a question again if its answer is already known.
   This includes testing other devices, networks, browsers,
   password resets, clearing cache, and troubleshooting steps.

6. Use the accumulated answers to narrow the investigation.
   Ask about a genuinely different missing fact that can help
   diagnose THIS issue. Do not restart the investigation.

7. If the customer says "that's all", "create the ticket now",
   "stop asking", or equivalent, stop investigation immediately.
   Mark information_complete true and preserve the summary.
   The backend should proceed to its existing confirmation flow.

8. Do not prolong the investigation unnecessarily.
   Prioritize information that makes the eventual ticket useful
   to the support team. Respect the customer's decision to stop.

IMPORTANT: UNDERSTAND THE CUSTOMER'S MEANING FIRST.

CRITICAL INVESTIGATION OVERRIDE:
- Use ONLY troubleshooting steps explicitly confirmed by the customer
  in the CURRENT conversation for this issue.
- Never assume cache clearing, incognito, password reset,
  another device, another network, or any other action was attempted.
- Previous conversations, unrelated sessions, examples, and generic
  assumptions are NOT evidence that a step was attempted.
- If a step has not been confirmed, treat it as NOT TRIED.
- Never offer ticket creation after only one diagnostic answer.
- Continue troubleshooting by asking ONE relevant question at a time.
- First suggest the simplest safe troubleshooting step that has
  not already been attempted.
- Ticket creation must not be suggested merely because information
  is incomplete. Continue investigation instead.
- If the customer explicitly requests a ticket, respect that request.


- Before requesting investigation details, determine whether the
  latest customer message has a clear and understandable meaning
  in the context of the conversation.
- A short statement that contains a number, amount, product or
  transaction reference is not automatically a clear explanation
  of the problem.
- If the customer's statement has multiple plausible meanings,
  do not choose one based on assumptions.
- Set action to UNCERTAIN and needs_clarification to true.
- Ask one simple question that distinguishes between the plausible
  meanings of the customer's statement.
- Do not request account usernames, transaction IDs, order IDs,
  screenshots or other sensitive or identifying details until
  the nature of the reported problem is sufficiently understood.
- Once the customer clarifies the problem, continue normal,
  issue-specific information collection.

1. Identify important information that is missing for investigating
   THIS PARTICULAR complaint.

2. Do not use the same checklist for every complaint.
   A delivery issue, login issue, payment issue and technical issue
   require different information.

3. Identify contradictions only when two customer statements genuinely
   conflict. Do not treat additional details as contradictions.

4. Identify explicit corrections separately.
   When a customer clearly corrects an earlier statement, use the
   corrected information in the updated summary.

5. Never silently choose between two conflicting facts.
   Ask the customer which information is correct.

6. If pending contradictions are provided, determine whether the
   latest customer message clearly resolves them.
   If resolved, set resolves_pending_contradiction to true,
   include the corrected fact in relevant_details and issue_summary,
   and do not report the resolved conflict again.
   If not resolved, keep the conflict and ask a specific clarification.

7. Never invent order IDs, dates, error messages, causes, device details
   or other customer information.

7. Do not ask for information already provided.

8. Ask only ONE next question. Choose the question that would be
   most useful for investigating the issue.

9. Never repeat a question listed under QUESTIONS ALREADY ASKED.
   If the customer has not answered a previous question, acknowledge
   that it remains unanswered. Prefer investigating another useful
   missing detail instead of asking the same question again.

9. If a contradiction needs clarification, prioritise resolving it
   before asking about other missing information.

10. Do not request an email address. The backend handles email collection.

11. information_complete means sufficient issue information has been
    gathered to proceed with the existing ticket summary process.
    It does NOT mean the problem itself has been resolved.

12. Do not mark the conversation COMPLETE unless the customer
    explicitly says they have finished.

THIRD: UPDATE THE ISSUE SUMMARY.

THIRD: UPDATE THE ISSUE SUMMARY.

IMPORTANT: The final issue summary must contain ONLY facts
relevant to the customer's actual support problem.

SOURCE OF TRUTH:
- Use the customer's messages as the source of facts.
- Use assistant messages only to understand the context of
  the customer's answers.
- Never treat an assistant message as proof that an action
  was completed.
- Never copy claims made by the bot into the issue summary
  unless independently confirmed by the customer.

INCLUDE:
- The original complaint.
- Product or service involved, if identified.
- Order ID or reference number, if provided.
- The actual problem reported.
- Requested refund, replacement or other resolution.
- Relevant location, dates or troubleshooting details.
- Information the customer explicitly refused or was
  unable to provide, when relevant.

EXCLUDE:
- Greetings and casual conversation.
- Repeated information.
- Questions about whether a ticket was raised.
- Questions about the bot's replies.
- Assistant-generated ticket numbers.
- Claims that a refund, replacement or return was initiated
  unless the backend actually confirms that action.
- Anything unrelated to the support issue.

FORMAT THE SUMMARY USING THESE LABELS WHEN APPLICABLE:

Issue:
Product:
Order ID:
Requested Resolution:
Relevant Details:
Information Not Provided:

Only include fields supported by the customer's messages.
Do not invent missing values.
Do not include empty fields.
Keep the summary concise and professional.

For GREETING, SIDE_QUESTION, UNRELATED, PAUSE and CANCEL,
return empty relevant_details and issue_summary.

Return ONLY valid JSON using this exact structure:

{{
    "action": "ADD_DETAIL",
    "confidence": 0.95,
    "relevant_details": "Only newly provided relevant information",
    "issue_summary": "Updated factual issue summary",
    "missing_information": [],
    "contradictions": [],
    "corrections": [],
    "resolves_pending_contradiction": false,
    "next_question": "One useful question, or empty string",
    "information_complete": false,
    "needs_clarification": false,
    "clarification_question": ""
}}

Additional rules:

- missing_information: array of specific missing facts.
- contradictions: array describing genuinely conflicting statements.
- corrections: array describing explicit customer corrections.
- next_question: one natural, specific follow-up question.
- information_complete: boolean.
- needs_clarification: boolean.
- clarification_question: use when the latest message is ambiguous
  or a contradiction must be clarified.

For UNCERTAIN, ask one specific clarification question.

For COMPLETE, preserve the complete factual summary.

For non-issue messages, do not modify the existing issue information.
"""

    try:
        response = llm.invoke(prompt)
        response_text = extract_response_text(response.content)
        result = parse_json_response(response_text)
    except Exception as exc:
        print(f"Ticket conversation analysis failed: {exc}")
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
            "missing_information": [],
            "contradictions": [],
            "corrections": [],
            "resolves_pending_contradiction": False,
            "next_question": "",
            "information_complete": False,
            "needs_clarification": True,
            "clarification_question": (
                "Could you clarify that information so I can "
                "understand your support issue correctly?"
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
        result.get("relevant_details") or ""
    ).strip()

    issue_summary = str(
        result.get("issue_summary") or ""
    ).strip()

    def clean_list(value):
        if not isinstance(value, list):
            return []
        return [
            str(item).strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]

    missing_information = clean_list(
        result.get("missing_information")
    )

    contradictions = clean_list(
        result.get("contradictions")
    )

    corrections = clean_list(
        result.get("corrections")
    )

    next_question = str(
        result.get("next_question") or ""
    ).strip()

    clarification_question = str(
        result.get("clarification_question") or ""
    ).strip()

    information_complete = (
        result.get("information_complete") is True
    )

    needs_clarification = (
        result.get("needs_clarification") is True
    )

    if action in {
        "GREETING",
        "SIDE_QUESTION",
        "UNRELATED",
        "PAUSE",
        "CANCEL",
    }:
        relevant_details = ""
        issue_summary = ""
        missing_information = []
        contradictions = []
        corrections = []
        next_question = ""
        information_complete = False
        needs_clarification = False
        clarification_question = ""

    return {
        "action": action,
        "confidence": round(confidence, 4),
        "relevant_details": relevant_details,
        "issue_summary": issue_summary,
        "missing_information": missing_information,
        "contradictions": contradictions,
        "corrections": corrections,
        "resolves_pending_contradiction": (
            result.get("resolves_pending_contradiction") is True
        ),
        "next_question": next_question,
        "information_complete": information_complete,
        "needs_clarification": needs_clarification,


        "clarification_question": clarification_question,
    }
