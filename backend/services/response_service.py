
"""Customer support response generation service."""


def generate_support_response(intent: str, message: str) -> str:

    if intent == "delivery_issue":

        return (
            "I'm sorry your order hasn't arrived yet. "
            "I can help you with this.\n\n"
            "Please try these steps:\n"
            "1. Open the Orders section of your account.\n"
            "2. Select your order and check its latest tracking status.\n"
            "3. Check whether the estimated delivery date has passed.\n"
            "4. If your order is delayed, contact the delivery support "
            "team with your order ID.\n\n"
            "Would you like help with anything else regarding your delivery?"
        )
    elif intent == "refund_request":
        return (
            "I understand your concern about the refund. "
        )
    else:
        return (
            "Thank you for reaching out. "
            "I will do my best to assist you with your issue."
        )
        
      
