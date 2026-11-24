from pathlib import Path
import shutil

path = Path("main.py")
source = path.read_text(encoding="utf-8-sig")
backup = Path("main.py.before_zep_emergency_fix.bak")
shutil.copy2(path, backup)

# 1. Remove the second, duplicate Zep start_user_turn() call.
duplicate_block = '''        finally:
            print(
                f"ZEP TOTAL TIME: "
                f"{time.perf_counter() - zep_start_time:.2f}s"
            )
        try:
            thread_uuid, zep_memory_context = start_user_turn(
                company_id="active_company",
                customer_id=customer_id,
                session_id=session_id,
                user_message=user_message,
            )

            if thread_uuid:
                state["zep_thread_uuid"] = thread_uuid

        except Exception as exc:
            print(f"ZEP: Memory integration failed: {exc}")
'''

single_block = '''        finally:
            print(
                f"ZEP TOTAL TIME: "
                f"{time.perf_counter() - zep_start_time:.2f}s"
            )
'''

# 2. Add a focused detector for physical robbery/theft emergencies.
helper_anchor = "def valid_email(email):"
emergency_helper = '''def is_urgent_safety_message(message):
    """Detect clear physical danger or robbery/theft situations."""
    normalized = re.sub(r"[^a-z0-9 ]+", " ", message.lower())
    normalized = re.sub(r"\\\\s+", " ", normalized).strip()

    direct_danger_terms = (
        "robbed", "robbery", "mugged", "mugging",
        "snatched", "snatching", "attacked", "assaulted",
        "kidnapped", "threatened",
    )

    financial_context_terms = (
        "atm", "cash", "money", "withdrawal",
        "wallet", "purse", "bank", "rupees",
    )

    has_direct_danger = any(
        term in normalized for term in direct_danger_terms
    )
    has_financial_context = any(
        term in normalized for term in financial_context_terms
    )

    describes_cash_robbery = (
        has_financial_context
        and any(term in normalized for term in (
            "pulled the money",
            "took the money",
            "grabbed the money",
            "escaped with",
            "ran away with",
            "stole the cash",
            "stole my money",
        ))
    )

    return (
        (has_direct_danger and has_financial_context)
        or describes_cash_robbery
    )


'''

# 3. Add emergency guidance before duplicate-ticket processing.
routing_anchor = '''    # ------------------------------------------------
    # STEP 1: HANDLE DUPLICATE CONFIRMATION
'''
emergency_routing = '''    # Handle urgent physical-safety incidents separately from company support.
    if is_urgent_safety_message(user_message):
        reply = (
            "I'm sorry this happened to you. Your safety comes first. "
            "If you are still in immediate danger, move to a safe public place "
            "and call India's emergency number 112.\\n\\n"
            "Since you described a robbery involving ATM cash, please report "
            "the incident to the police as soon as possible. Contact your bank "
            "immediately to report the incident and ask them to review the "
            "withdrawal and secure your account or card if necessary.\\n\\n"
            "Keep the ATM location, transaction time, bank SMS or receipt, "
            "and any details about the people or vehicle for the police. "
            "Do not approach or confront the suspects.\\n\\n"
            "If money was also transferred electronically without your "
            "permission, report that financial cyber fraud through India's "
            "1930 helpline as well. This chatbot cannot contact the police "
            "or your bank on your behalf."
        )

        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            conversation_status="urgent_safety_guidance",
            response_source="urgent_safety_guidance",
        )

'''

# 4. If the customer repeats the human request while email is pending,
# explain that email is needed instead of calling it an invalid email.
email_anchor = '''        if current_step == "customer_email":
            email = user_message.strip()
'''
email_replacement = '''        if current_step == "customer_email":
            if wants_human_support(user_message):
                reply = (
                    "I understand that you want to speak with a human. "
                    "Your support request is ready for human follow-up. "
                    "Please provide your email address so the support team "
                    "can contact you."
                )
                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    awaiting_customer_email=True,
                    conversation_status="collecting_customer_email",
                )

            email = user_message.strip()
'''

checks = [
    (duplicate_block, single_block, "duplicate Zep call"),
    (helper_anchor, emergency_helper + helper_anchor, "emergency detector insertion"),
    (routing_anchor, emergency_routing + routing_anchor, "emergency routing insertion"),
    (email_anchor, email_replacement, "repeated human request during email collection"),
]

for old, new, label in checks:
    count = source.count(old)
    if count != 1:
        raise SystemExit(
            f"STOP: Expected exactly one match for {label}, found {count}. "
            "No changes were written."
        )
    source = source.replace(old, new, 1)

path.write_text(source, encoding="utf-8-sig")
print("All four changes applied successfully.")
print(f"Backup saved as: {backup}")
