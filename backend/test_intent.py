
from services.complaint_service import classify_complaint

test_messages = [
    "My payment was deducted twice.",
    "Where is my order? It has not arrived.",
    "I want to get my money back.",
    "I cannot log into my account.",
    "How can I cancel my order?",
    "I want to know more about your product."
]

for message in test_messages:

    result = classify_complaint(message)

    print("\nCustomer:", result["message"])
    print("Predicted intent:", result["intent"])
    print("Confidence:", result["confidence"])
    print("-" * 50)
