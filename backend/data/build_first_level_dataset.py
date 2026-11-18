
import csv
import random
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "first_level_dataset.csv"

random.seed(42)

DATA = {
    "BUSINESS_ENQUIRY": [        ("Could you walk me through what your company provides?", "services"),
        ("I'm exploring options and would like to know what you offer.", "services"),
        ("Can I get a breakdown of the different plans?", "pricing"),
        ("Is there a way to try the platform before committing?", "trial"),
        ("I'd like to arrange a meeting to discuss your services.", "booking"),
        ("Do you have a solution suitable for small businesses?", "services"),
        ("Can you send me information about your offerings?", "services"),
        ("What would it cost to use your service?", "pricing"),
        ("I'd like to know whether you offer flexible packages.", "pricing"),
        ("Can I get a personalized quotation?", "quotation"),
        ("What services do you offer?", "services"),
        ("Can you tell me about your available plans?", "pricing"),
        ("How much does your service cost?", "pricing"),
        ("I would like to know more about your offerings.", "services"),
        ("Can I get a quotation for your services?", "quotation"),
        ("Do you provide customized solutions?", "services"),
        ("What features are included in your platform?", "features"),
        ("Can I schedule a demonstration?", "booking"),
        ("I am interested in purchasing your service.", "purchase"),
        ("Do you offer any premium plans?", "pricing"),
        ("What are the available subscription options?", "pricing"),
        ("Can someone explain your service packages?", "services"),
        ("I want to compare your available plans.", "comparison"),
        ("Do you provide enterprise solutions?", "services"),
        ("Can I request a business proposal?", "quotation"),
        ("Is there a free trial available?", "trial"),
        ("How can I become a customer?", "onboarding"),
        ("I would like to discuss a business partnership.", "partnership"),
        ("Can you tell me about your service capabilities?", "features"),
        ("What are the benefits of choosing your company?", "services"),
        ("I want to book a consultation.", "booking"),
        ("Are there different packages available?", "pricing"),
        ("Can I speak with someone about your offerings?", "sales"),
        ("Please share details about your available solutions.", "services"),
        ("I would like to request a price estimate.", "quotation"),        ("I'm looking for a service that can meet our business needs.", "services"),
        ("Would it be possible to get a walkthrough of your platform?", "demonstration"),
        ("We're considering your company for an upcoming project.", "business_interest"),
        ("I need to understand the costs before making a decision.", "pricing"),
        ("Could your team help us choose the right package?", "consultation"),
        ("I'd like to explore whether your services suit our requirements.", "services"),
        ("Is your service suitable for a growing organization?", "services"),
        ("We may be interested in working with your company.", "partnership"),
        ("Can I arrange a discussion with your sales team?", "sales"),
        ("What options would you recommend for a new customer?", "recommendation"),        ("How do your different plans compare with each other?", "comparison"),
        ("What makes one package different from another?", "comparison"),
        ("Could you demonstrate how the platform works?", "demonstration"),
        ("Can I arrange a consultation before choosing a service?", "consultation"),
        ("What is the process for getting started?", "onboarding"),
        ("I'd like to proceed with one of your offerings.", "purchase"),
        ("Can you explain what is included in each package?", "features"),
        ("Do you have a solution that fits my requirements?", "recommendation"),
    ],

    "CUSTOMER_SUPPORT": [        ("I've been trying to log in, but it won't let me.", "account"),
        ("Something went wrong with my recent transaction.", "payment"),
        ("Can someone from support look into this?", "human_support"),
        ("I've already reported this issue, but it hasn't been fixed.", "escalation"),
        ("The website keeps showing me an error.", "technical"),
        ("I think there's a mistake in my bill.", "billing"),
        ("I can't get into my profile anymore.", "account"),
        ("Please help me resolve my pending issue.", "general_issue"),
        ("My previous support request is still unanswered.", "existing_request"),
        ("I need to discontinue my current subscription.", "cancellation"),
        ("I am unable to access my account.", "account"),
        ("My payment was deducted but the transaction failed.", "payment"),
        ("I need help resolving a technical problem.", "technical"),
        ("I want to speak to a human support agent.", "human_support"),
        ("The service is not working as expected.", "technical"),
        ("I forgot my password and cannot log in.", "account"),
        ("I want to raise a complaint.", "complaint"),
        ("How can I report a problem?", "complaint"),
        ("I was charged incorrectly.", "billing"),
        ("I need help with an existing request.", "existing_request"),
        ("My account has been locked.", "account"),
        ("I want to cancel my subscription.", "cancellation"),
        ("I have not received a response to my previous complaint.", "complaint"),
        ("There is an error when I use this service.", "technical"),
        ("I need assistance with a failed transaction.", "payment"),
        ("Please help me recover my account.", "account"),
        ("I want to request a refund.", "refund"),
        ("The application keeps crashing.", "technical"),
        ("I am facing an issue with my registration.", "account"),
        ("I want to escalate my existing complaint.", "escalation"),
        ("My service suddenly stopped working.", "technical"),
        ("I need an update on my support request.", "existing_request"),
        ("I was billed twice for the same service.", "billing"),
        ("How do I contact your support team about a problem?", "human_support"),
        ("I am experiencing an issue and need assistance.", "general_issue"),        ("I've followed the instructions, but the problem remains.", "technical"),
        ("I keep getting sent back to the login page.", "account"),
        ("Something doesn't seem right with the amount charged.", "billing"),
        ("I have been waiting for help for quite some time.", "existing_request"),
        ("The feature worked yesterday but not today.", "technical"),
        ("I don't understand why my account access was removed.", "account"),
        ("Could you check what happened to my earlier request?", "existing_request"),
        ("I need someone to take responsibility for fixing this.", "escalation"),
        ("I was expecting a confirmation, but nothing arrived.", "general_issue"),
                ("I paid for the service but my account still shows unpaid.", "payment"),
        ("The payment keeps failing whenever I try.", "payment"),
        ("I would like my money returned for this transaction.", "refund"),
        ("How long will it take to receive my refund?", "refund"),
        ("I want to stop using the service and end my subscription.", "cancellation"),
        ("I am unhappy with how my issue was handled.", "complaint"),
        ("I have raised this several times without a solution.", "escalation"),
        ("Please transfer this issue to someone who can resolve it.", "human_support"),("This problem is preventing me from using the service.", "technical"),
    ],

    "GENERAL_QUERY": [
        ("Hello!", "greeting"),        ("What does your company specialize in?", "company_information"),
        ("What is the main purpose of this service?", "definition"),
        ("Where can I find your contact details?", "contact_information"),
        ("What are the usual ways to reach your company?", "contact_information"),
        ("What tasks can you assist me with?", "capabilities"),
        ("Can you explain the meaning of this feature?", "definition"),
        ("Where can I find the different sections of this website?", "navigation"),
        ("When is your office normally open?", "business_information"),
        ("Hi, how are you?", "greeting"),
        ("Good morning.", "greeting"),
        ("Thank you for your help.", "gratitude"),
        ("What is your company about?", "company_information"),
        ("Who are you?", "identity"),
        ("What can you help me with?", "capabilities"),
        ("Can you explain how this website works?", "website_information"),
        ("Where can I find the information section?", "navigation"),
        ("What are your working hours?", "business_information"),
        ("Where is your company located?", "company_information"),
        ("How can I contact your company?", "contact_information"),
        ("Can you explain what this platform does?", "platform_information"),
        ("I have a general question.", "general_information"),
        ("Can you help me understand this topic?", "general_information"),
        ("What does this term mean?", "definition"),
        ("Tell me something interesting.", "casual_conversation"),
        ("Goodbye!", "farewell"),
        ("Have a nice day.", "farewell"),
        ("Can you introduce yourself?", "identity"),
        ("Where can I find your privacy policy?", "website_information"),
        ("Is this website available on mobile?", "website_information"),
        ("I just wanted to say hello.", "greeting"),
        ("Thanks, that answers my question.", "gratitude"),
        ("Can you provide some general information?", "general_information"),
                 ("Hey there!", "greeting"),
        ("I hope you're doing well.", "greeting"),
        ("What kind of company is this?", "company_information"),
        ("Can you tell me a little about this website?", "website_information"),
        ("Where should I look for more information?", "navigation"),
        ("Are you available throughout the day?", "business_information"),
        ("What is the purpose of this platform?", "platform_information"),
        ("Could you explain that in simpler words?", "general_information"),
        ("That's all I wanted to know, thanks.", "gratitude"),
        ("See you later!", "farewell"),        ("Before we begin, could you introduce your company?", "company_information"),
        ("I'm just looking around your website.", "website_information"),
        ("What does your organization generally do?", "company_information"),
        ("Could you point me in the right direction?", "navigation"),
        ("Is there somewhere I can read about your company?", "company_information"),
        ("I have a question that isn't related to a purchase.", "general_information"),
        ("Can you explain the purpose of this website?", "website_information"),
        ("Who developed this platform?", "platform_information"),
        ("I was just curious about your organization.", "company_information"),
        ("That's interesting. Tell me a little more.", "casual_conversation"),
    ],
    
}


def build_dataset():
    rows = []

    for intent, examples in DATA.items():
        for text, scenario in examples:
            rows.append({
                "text": text,
                "intent": intent,
                "scenario": scenario
            })

    random.shuffle(rows)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["text", "intent", "scenario"]
        )
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(row["intent"] for row in rows)

    print("First-level dataset created successfully.")
    print("Total examples:", len(rows))
    print("Category distribution:")

    for intent, count in sorted(counts.items()):
        print(f"{intent}: {count}")

    print("Saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    build_dataset()
