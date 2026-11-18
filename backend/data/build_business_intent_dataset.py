
import csv
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "business_intent_dataset.csv"

DATA = {
    "PRICING_ENQUIRY": [
        "How much does this service cost?",
        "What are your pricing plans?",
        "Can you tell me the monthly subscription fee?",
        "Is there an additional setup charge?",
        "Do you offer discounts for bulk purchases?",
        "What is the cheapest available plan?",
        "How much will the complete package cost?",
        "Are there any hidden charges?",
        "What is the annual subscription price?",
        "Can I get your price list?",
    ],
    "FEATURE_ENQUIRY": [
        "What features does your software provide?",
        "Does this product support cloud storage?",
        "Can I integrate this service with other tools?",
        "What capabilities are included in the premium plan?",
        "Does your platform support multiple users?",
        "Can you explain how this feature works?",
        "Does the service provide automatic backups?",
        "What functionalities are available?",
        "Can I customize the software?",
        "Does this product support mobile devices?",
    ],
    "PRODUCT_SERVICE_ENQUIRY": [
        "Tell me more about your products.",
        "What services does your company provide?",
        "I want details about your premium package.",
        "Do you have laptops with RTX graphics?",
        "Can you explain your consulting services?",
        "What models are available?",
        "Tell me about your travel packages.",
        "I need information about your software.",
        "What solutions do you offer for businesses?",
        "Can you share the specifications of this product?",
    ],
    "COMPARISON_ENQUIRY": [
        "Which plan is better for a small business?",
        "Compare your basic and premium plans.",
        "What is the difference between these two products?",
        "Which laptop is better for gaming?",
        "Can you compare both service packages?",
        "How does this model differ from the previous one?",
        "Which option provides better value?",
        "Compare the features of these products.",
        "Which subscription should I choose?",
        "What are the advantages of each package?",
    ],
    "AVAILABILITY_ENQUIRY": [
        "Is this product currently in stock?",
        "Are rooms available this weekend?",
        "Do you have an appointment slot tomorrow?",
        "Is this service available in my city?",
        "When will this model be available?",
        "Are there any seats left?",
        "Can I check the availability of this package?",
        "Is the product available for immediate delivery?",
        "Do you have this item in stock?",
        "Are consultations available next week?",
    ],
    "BOOKING_ENQUIRY": [
        "I want to book an appointment.",
        "Can you reserve a hotel room for me?",
        "How do I schedule a consultation?",
        "I would like to book a travel package.",
        "Can I reschedule my appointment?",
        "How can I reserve a seat?",
        "I need to make a reservation.",
        "Can you help me book a service?",
        "I want to change my booking date.",
        "How do I confirm my appointment?",
    ],
    "PURCHASE_ENQUIRY": [
        "I want to buy this product.",
        "How can I place an order?",
        "I am interested in purchasing this model.",
        "Can I order this package online?",
        "I would like to proceed with the purchase.",
        "Where can I buy this item?",
        "How do I purchase your subscription?",
        "I want to order two units.",
        "Can you help me complete my purchase?",
        "I am ready to buy this product.",
    ],
    "DEMO_ENQUIRY": [
        "Can I schedule a product demonstration?",
        "Do you offer a free trial?",
        "I would like to see a demo.",
        "Can someone demonstrate the software?",
        "How can I request a trial account?",
        "Can I test the platform before buying?",
        "I want a live demonstration.",
        "Is a trial version available?",
        "Can you arrange a consultation?",
        "I would like to try your service.",
    ],
    "QUOTATION_ENQUIRY": [
        "Can you send me a formal quotation?",
        "I need an estimate for 50 units.",
        "Please provide a price quote for my company.",
        "Can I get a written cost estimate?",
        "I need a quotation for your services.",
        "How do I request a business quote?",
        "Can you prepare an estimate for this project?",
        "Please share a detailed quotation.",
        "I need a quote for bulk orders.",
        "Can you provide a proposal with pricing?",
    ],
    "PARTNERSHIP_ENQUIRY": [
        "Are you open to business partnerships?",
        "I want to become your business partner.",
        "Do you offer reseller opportunities?",
        "How can we collaborate with your company?",
        "I am interested in a distribution partnership.",
        "Do you work with affiliates?",
        "Can we discuss a strategic partnership?",
        "I want to become an authorized dealer.",
        "Does your company support channel partners?",
        "How can my company collaborate with yours?",
    ],
    "OTHER_BUSINESS_ENQUIRY": [
        "Where is your company headquarters?",
        "Who should I contact for corporate enquiries?",
        "What are your business hours?",
        "Do you serve international customers?",
        "Can you share your company profile?",
        "Where are your branches located?",
        "How long has your company been operating?",
        "Do you provide services outside India?",
        "I need your sales department contact details.",
        "Can you tell me about your company?",
    ],
}

def build_dataset():
    random.seed(42)
    rows = []

    for intent, examples in DATA.items():
        for sentence in examples:
            rows.append({"text": sentence, "intent": intent})

    random.shuffle(rows)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["text", "intent"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Dataset created: {OUTPUT_PATH}")
    print(f"Total examples: {len(rows)}")
    print(f"Number of intents: {len(DATA)}")

    for intent, examples in DATA.items():
        print(f"{intent}: {len(examples)}")


if __name__ == "__main__":
    build_dataset()
