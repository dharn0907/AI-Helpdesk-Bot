import csv
import random
import re
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "intent_dataset.csv"
BACKUP_PATH = BASE_DIR / "intent_dataset_backup_8_categories.csv"

random.seed(42)

EXAMPLES = {
    "return_request": [
        "I want to return the laptop I purchased.",
        "How can I return a product?",
        "I would like to send this item back.",
        "The product does not meet my expectations, so I want to return it.",
        "Can you arrange a return for my order?",
        "I received the product but want to return it.",
        "Please tell me your product return procedure.",
        "I want to initiate a return for my purchase.",
        "Can I return an unopened product?",
        "I changed my mind and want to return the item.",
        "Please help me send the product back.",
        "I am not satisfied with the product and want to return it.",
        "What is the process for returning a laptop?",
        "I want to request a return for my recent purchase.",
        "Can you arrange a pickup for my returned product?",
        "The product is different from what I expected. I want to return it.",
        "I no longer need this item and would like to return it.",
        "How many days do I have to return a product?",
        "I want to return the product delivered yesterday.",
        "Please guide me through the return process.",
    ],
    "order_status_enquiry": [
        "Where is my order right now?",
        "Can you check the status of my order?",
        "Has my order been confirmed?",
        "Is my order still being processed?",
        "When will my order be shipped?",
        "I want to know the current status of my purchase.",
        "Has my package been dispatched?",
        "Can I get an update about my order?",
        "What is the tracking status of my order?",
        "Is my order confirmed in your system?",
        "When can I expect my order to be shipped?",
        "Has the seller processed my order?",
        "Please provide an update on my purchase.",
        "I have placed an order and want to check its progress.",
        "Can you tell me whether my order is confirmed?",
        "Is my package ready for dispatch?",
        "Where can I track my purchase?",
        "I want to know if my order has been packed.",
        "Has my order moved to the shipping stage?",
        "Can you tell me the estimated dispatch date?",
    ],
    "exchange_request": [
        "I want to exchange the laptop for another model.",
        "Can I exchange my product for a different variant?",
        "I received the wrong size and want an exchange.",
        "How can I request a product exchange?",
        "I would like to replace this item with another model.",
        "Can you help me exchange my purchase?",
        "I want the same product in a different colour.",
        "Please arrange an exchange for my order.",
        "Can I exchange my laptop for a higher configuration?",
        "I selected the wrong variant. Can I exchange it?",
        "I want to swap this product for another one.",
        "Is product exchange available for my order?",
        "I need a different model instead of this one.",
        "Can I get an exchange instead of a refund?",
        "Please tell me the steps to exchange a product.",
        "I want to replace my current item with another variant.",
        "Can I exchange the product I received yesterday?",
        "I ordered the wrong model and need an exchange.",
        "How long does the product exchange process take?",
        "Please help me request a different product variant.",
    ],
    "warranty_request": [
        "Is my laptop still covered under warranty?",
        "How can I claim my product warranty?",
        "I need to register a warranty claim.",
        "What is the warranty period for this laptop?",
        "My product stopped working and I want warranty service.",
        "Can you check whether my device is under warranty?",
        "How do I get my laptop repaired under warranty?",
        "I want to know the warranty coverage for my purchase.",
        "Where can I submit a warranty claim?",
        "Does the warranty cover accidental damage?",
        "My laptop has a hardware problem. Can I claim warranty?",
        "Please explain the warranty claim procedure.",
        "When does my product warranty expire?",
        "I need assistance with a warranty replacement.",
        "Can I get a free repair under the product warranty?",
        "Is the battery covered under warranty?",
        "My device is malfunctioning during the warranty period.",
        "How can I contact the warranty service centre?",
        "I want to check my warranty eligibility.",
        "Please help me with my laptop warranty claim.",
    ],
}

EXISTING_ADDITIONS = {
    "product_issue": [
        "My laptop keeps restarting unexpectedly.",
        "The keyboard on my laptop is not responding.",
        "My screen flickers whenever I open an application.",
        "The touchpad has stopped working.",
        "My laptop becomes extremely hot during normal use.",
        "The speakers are producing distorted sound.",
        "The battery drains very quickly.",
        "My laptop does not detect the external monitor.",
        "The webcam is not working during video calls.",
        "The Wi-Fi keeps disconnecting on my device.",
        "My laptop is making an unusual noise.",
        "The charging port feels loose.",
        "The display has developed a bright line.",
        "My laptop freezes when I open multiple applications.",
        "The fingerprint sensor is not detecting my finger.",
        "The USB ports are not recognizing my devices.",
        "The fan runs continuously even when idle.",
        "My laptop takes too long to start.",
        "The audio suddenly stops working.",
        "The trackpad sometimes moves on its own.",
        "My laptop shuts down without warning.",
        "The screen brightness cannot be adjusted.",
        "The graphics performance is much slower than expected.",
        "My device cannot detect Bluetooth headphones.",
        "The power button is not responding properly.",
        "The laptop camera shows a black screen.",
        "My keyboard keys are typing incorrect characters.",
        "The operating system crashes repeatedly.",
        "My laptop does not recognize the charger.",
        "The display resolution keeps changing automatically.",
        "My device becomes very slow after an update.",
        "The microphone is not picking up my voice.",
        "The laptop hinge makes a clicking sound.",
        "My laptop is stuck on the startup logo.",
        "The battery percentage jumps unexpectedly.",
        "The screen goes black while I am working.",
        "My laptop cannot connect to my home Wi-Fi.",
        "The touchpad gestures have stopped working.",
        "My device keeps showing blue screen errors.",
        "The laptop does not wake up from sleep mode.",
        "The cooling system is not working properly.",
        "My laptop is experiencing graphics glitches.",
        "The display has dead pixels.",
        "The keyboard backlight is not turning on.",
        "My laptop restarts whenever I play games.",
        "The audio jack is not detecting my earphones.",
        "My device is not recognizing an SD card.",
        "The laptop battery is not charging fully.",
        "My laptop is running much slower than before.",
        "The screen has started flickering randomly.",
    ],
    "account_issue": [
        "I need to change the email linked to my account.",
        "How can I update my registered phone number?",
        "My profile information is incorrect.",
        "I want to change my account details.",
        "How do I delete my customer account?",
        "I cannot update my billing address.",
        "My account profile is showing outdated information.",
        "I want to add another address to my account.",
        "How can I remove an old delivery address?",
        "I need to update my personal information.",
        "My account is showing the wrong name.",
        "Can I change the mobile number on my profile?",
        "I want to deactivate my account.",
        "How can I manage my saved addresses?",
        "My account details are not getting saved.",
        "I need to change my communication preferences.",
        "Can I update my registered email address?",
        "I want to remove an old phone number.",
        "My profile picture is not updating.",
        "How do I edit my customer information?",
        "I accidentally entered the wrong address in my profile.",
        "I need help changing my account settings.",
        "Can I have multiple delivery addresses?",
        "My saved billing details have disappeared.",
        "I want to close my shopping account permanently.",
        "How do I change the name displayed on my profile?",
        "I cannot save changes to my account.",
        "My registered contact information needs updating.",
        "I want to add a new phone number to my profile.",
        "How can I update my account preferences?",
        "My account information is not displaying correctly.",
        "I need to remove an address from my profile.",
        "Can I change the email used for account notifications?",
        "My profile changes are not reflecting.",
        "I want to update my billing information.",
        "How can I edit my saved contact details?",
        "I need to change my account's registered details.",
        "My delivery address is outdated.",
        "Can I update my profile from the website?",
        "I want to permanently delete my profile.",
        "My account is displaying someone else's details.",
        "How do I change my preferred contact method?",
        "I need to correct my account information.",
        "The address update option is not working.",
        "I want to manage the addresses saved in my account.",
        "My phone number in the profile is incorrect.",
        "Can I update my account without creating a new one?",
        "I need to change my customer profile details.",
        "My saved account preferences are missing.",
        "How do I update my registered billing address?",
    ],
    "payment_issue": [
        "My card was charged but the transaction failed.",
        "The payment page keeps showing an error.",
        "I cannot pay using my debit card.",
        "My UPI transaction is still pending.",
        "The website rejected my payment.",
        "I was charged twice for the same purchase.",
        "The payment gateway is not opening.",
        "My bank shows a debit but the website shows unpaid.",
        "I cannot complete checkout using net banking.",
        "The wallet balance was deducted incorrectly.",
        "My transaction failed after entering the OTP.",
        "The payment button does not respond.",
        "I received a payment error despite sufficient balance.",
        "My credit card payment is being declined.",
        "The transaction is stuck on processing.",
        "My payment was successful but no receipt arrived.",
        "I cannot use UPI to pay for my order.",
        "The payment amount is different from the checkout total.",
        "My bank account was debited but payment is unsuccessful.",
        "The website keeps asking me to pay again.",
        "I was charged an unexpected additional amount.",
        "My payment was reversed immediately.",
        "The checkout page crashed during payment.",
        "I cannot use my saved card for payment.",
        "The payment verification failed.",
        "My transaction reference shows success but the order is unpaid.",
        "The payment gateway timed out.",
        "I am unable to complete the payment through UPI.",
        "My card payment is pending for several hours.",
        "The payment option disappeared during checkout.",
        "I accidentally made two payments for one order.",
        "My prepaid wallet payment is not going through.",
        "The bank declined a transaction that should have worked.",
        "I cannot enter my card details on the payment page.",
        "The payment status is not updating.",
        "My transaction was interrupted during checkout.",
        "The website deducted more money than expected.",
        "I am getting an invalid transaction error.",
        "My payment confirmation has not appeared.",
        "The payment page keeps loading without completing.",
        "I cannot pay through internet banking.",
        "My UPI app shows success but the store shows failure.",
        "The transaction was cancelled after money was deducted.",
        "My payment is stuck in an unknown status.",
        "The checkout system is not accepting my payment.",
        "I received a duplicate payment notification.",
        "My card payment was processed but the order was not.",
        "The payment gateway is showing a server error.",
        "My transaction failed even though the amount was debited.",
        "I need help with an incorrect payment charge.",
    ],    "delivery_issue": [
        "My package has not arrived by the promised date.",
        "The courier delivered my parcel to the wrong address.",
        "My tracking says delivered but I did not receive anything.",
        "The delivery person did not contact me.",
        "My package arrived with damaged outer packaging.",
        "The courier keeps postponing the delivery.",
        "I received someone else's package.",
        "My parcel is stuck at the sorting centre.",
        "The delivery address was ignored by the courier.",
        "My package has been missing for several days.",
        "The delivery agent marked me unavailable without visiting.",
        "My shipment has not moved for a week.",
        "The courier attempted delivery at the wrong location.",
        "I received an incomplete shipment.",
        "My package was delivered to my neighbour without permission.",
        "The parcel arrived later than the estimated date.",
        "The delivery status says returned but I never received it.",
        "My order is stuck in transit.",
        "The delivery agent is unable to locate my address.",
        "The package was left outside without informing me.",
        "My shipment has been delayed repeatedly.",
        "The courier says my address is incorrect.",
        "The parcel was damaged during transportation.",
        "I received an empty delivery package.",
        "My order was delivered to a different building.",
        "The tracking information has not changed.",
        "My package is missing after being marked out for delivery.",
        "The courier has not attempted delivery yet.",
        "My shipment was sent back without my approval.",
        "The package arrived with missing accessories.",
        "My delivery has been rescheduled multiple times.",
        "The courier delivered my order to the wrong person.",
        "My parcel has not arrived despite the tracking estimate.",
        "The delivery agent refuses to deliver to my location.",
        "My order was marked as delivered but is still missing.",
    ],
    "cancellation_request": [
        "Please cancel my recently placed order.",
        "I no longer want to purchase this item.",
        "Can you stop my order before it ships?",
        "I accidentally ordered the same product twice.",
        "Please cancel my subscription renewal.",
        "I selected the wrong product and want to cancel.",
        "I changed my mind about this purchase.",
        "I want to withdraw my order.",
        "Please stop processing my purchase.",
        "Do not dispatch my order.",
        "I want to cancel one item from my order.",
        "Can I cancel an order that has not shipped?",
        "I placed the order by mistake.",
        "Please cancel my service booking.",
        "I no longer need this product.",
        "I want to discontinue my monthly subscription.",
        "Please cancel the duplicate order.",
        "Can you cancel my purchase request?",
        "I do not want this order anymore.",
        "Please stop the automatic renewal of my plan.",
        "I want to cancel the order before dispatch.",
        "I selected the wrong configuration and want to cancel.",
        "Please withdraw my purchase request.",
        "I want to stop my subscription from next month.",
        "Can you cancel my booking?",
        "I no longer wish to proceed with this order.",
        "Please cancel my order as soon as possible.",
        "I want to cancel the product I ordered yesterday.",
        "My requirements changed and I need to cancel.",
        "Please remove this purchase from my orders.",
        "I want to cancel my pending order.",
        "Can you stop the shipment and cancel my order?",
        "I ordered the item accidentally and want to cancel.",
        "Please cancel my scheduled service.",
        "I don't want to continue with this purchase.",
    ],
    "refund_request": [
        "My refund has not reached my bank account.",
        "When will the cancelled order amount be refunded?",
        "I have not received the refund confirmation.",
        "The refund was approved but the money is missing.",
        "I received only part of my refund.",
        "Please check the status of my pending refund.",
        "The promised refund date has passed.",
        "My refund is still not credited.",
        "I returned the product but have not received my money.",
        "The refund amount is incorrect.",
        "I need an update on my refund.",
        "My refund request has been pending for days.",
        "The refund was initiated but not received.",
        "I want my money back for the cancelled purchase.",
        "The refund is not visible in my bank statement.",
        "Can you tell me when I will receive the refund?",
        "I received a refund notification but no credit.",
        "My payment reversal has not happened.",
        "Please investigate my missing refund.",
        "The returned product was accepted but the refund is pending.",
        "I was promised a refund that never arrived.",
        "My refund was sent to the wrong payment method.",
        "The refund amount does not match what I paid.",
        "I want to know why my refund is delayed.",
        "The refund status has not changed.",
        "I cancelled my order but the amount is still not returned.",
        "My refund transaction failed.",
        "Please process the outstanding refund.",
        "I have been waiting too long for my refund.",
        "The refund has not appeared on my card statement.",
        "Can you verify whether my refund was processed?",
        "I received less money than expected as a refund.",
        "My return was completed but the refund is missing.",
        "Please help me recover the money from my cancelled order.",
        "I need assistance with a delayed refund.",
    ],
    "general_enquiry": [
        "What are your customer support hours?",
        "Do you offer installation services?",
        "Where can I find your product catalogue?",
        "Do you provide student discounts?",
        "What payment methods do you accept?",
        "Can I purchase an extended warranty?",
        "Do you have a physical store?",
        "How can I contact customer support?",
        "Do you provide product demonstrations?",
        "What are your return policy conditions?",
        "Do you offer free delivery?",
        "Where can I read your privacy policy?",
        "Do you have any ongoing promotions?",
        "Can I buy accessories separately?",
        "Do you support international shipping?",
        "What is the process for creating an account?",
        "Do you offer financing options?",
        "How can I compare two laptop models?",
        "Are your products available in different colours?",
        "Do you provide invoices for purchases?",
        "Can I place an order over the phone?",
        "Where can I find the user manual?",
        "Do you offer business or bulk purchase pricing?",
        "What is your exchange policy?",
        "Can I visit your showroom?",
        "Do you provide technical support after purchase?",
        "How do I subscribe to product updates?",
        "Are refurbished products available?",
        "Do you have a loyalty rewards programme?",
        "Can I use multiple discount coupons?",
        "Where can I read the terms and conditions?",
        "Do you offer gift cards?",
        "How can I learn about your latest products?",
        "Do you provide setup assistance?",
        "What documents are needed for a business purchase?",
        "Can I get a quotation before purchasing?",
        "Do you have a price matching policy?",
        "Are accessories included with the laptop?",
        "How can I find your service centre locations?",
        "Do you provide online product support?",
        "Can I request a product demonstration?",
        "Do you offer discounts on bulk orders?",
        "Where can I find information about your company?",
        "Can I download product specifications?",
        "Do you have a newsletter?",
        "What are the available customer support channels?",
        "Can I purchase a gift for someone else?",
        "Do you provide corporate purchasing services?",
        "How can I learn about your available services?",
        "Where can I find your frequently asked questions?",
    ],
    "login_issue": [
        "I forgot my password and cannot sign in.",
        "My login credentials are being rejected.",
        "The website keeps logging me out.",
        "I cannot access my account after entering the password.",
        "The password reset link is not working.",
        "I am not receiving the login verification code.",
        "The login page freezes when I submit my details.",
        "My account login keeps failing.",
        "I cannot sign in using my registered email.",
        "The one-time password is not arriving.",
        "I keep getting an incorrect password message.",
        "The login button does nothing when clicked.",
        "I am locked out after several login attempts.",
        "The authentication code has expired.",
        "I cannot log in even after resetting my password.",
        "The sign-in page shows an unexpected error.",
        "My login session expires immediately.",
        "I am unable to access the website using my credentials.",
        "The verification email for login never arrived.",
        "My account password is not being accepted.",
        "I cannot complete two-factor authentication.",
        "The login screen keeps refreshing.",
        "I am unable to sign in from my new device.",
        "The system does not recognize my email during login.",
        "I entered the correct password but login fails.",
        "The password recovery process is not completing.",
        "I cannot receive the OTP needed to sign in.",
        "My login attempt keeps returning to the sign-in page.",
        "The website says my session is invalid.",
        "I cannot access my account after changing my password.",
        "The sign-in form is not accepting my credentials.",
        "I am having trouble logging in through the mobile app.",
        "The login verification code is incorrect.",
        "My account keeps getting signed out automatically.",
        "I cannot get past the authentication screen.",
        "The password reset email is not being delivered.",
        "I am unable to log in after enabling two-factor verification.",
        "My sign-in request is timing out.",
        "The website displays a login authentication error.",
        "I cannot access my account using the saved password.",
        "The login OTP arrives too late to use.",
        "I am stuck on the login page.",
        "My credentials work elsewhere but not on this website.",
        "The account sign-in process is not responding.",
        "I cannot log in after multiple password reset attempts.",
        "The login page says verification failed.",
        "My account is not accepting the correct OTP.",
        "I cannot sign in through my browser.",
        "The login process keeps showing an unknown error.",
        "I need help recovering access to my account.",
    ],
}


def normalize(text):
    return re.sub(r"\s+", " ", text.strip().lower())


PREFIXES = [
    "Please help me: ",
    "I need support: ",
    "Could you assist me? ",
    "I would like to ask: ",
    "I am contacting support because ",
]

SUFFIXES = [
    " Please advise me on the next step.",
    " Could you explain how to proceed?",
    " I would appreciate your guidance.",
    " Please let me know what I should do.",
]


def candidate_forms(message):
    yield message

    lowered = message[0].lower() + message[1:] if message else message

    for prefix in PREFIXES:
        yield prefix + lowered

    for suffix in SUFFIXES:
        yield message.rstrip().rstrip(".") + suffix


def add_unique_examples(target, intent, messages, required_count, seen):
    added = 0

    for message in messages:
        key = (intent, normalize(message))

        if key not in seen and added < required_count:
            target.append({
                "text": message,
                "intent": intent
            })

            seen.add(key)
            added += 1

    if added < required_count:
        for message in messages:
            for candidate in candidate_forms(message):
                key = (intent, normalize(candidate))

                if key in seen:
                    continue

                target.append({
                    "text": candidate,
                    "intent": intent
                })

                seen.add(key)
                added += 1

                if added == required_count:
                    break

            if added == required_count:
                break

    if added != required_count:
        raise ValueError(
            f"Could only create {added} unique additions for {intent}; "
            f"needed {required_count}. No CSV file was modified."
        )


def main():

    if not CSV_PATH.exists() or not BACKUP_PATH.exists():
        raise FileNotFoundError(
            "Dataset or original backup is missing."
        )

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames != ["text", "intent"]:
            raise ValueError(
                "Unexpected CSV columns. Expected: text,intent"
            )

        original_rows = list(reader)

    with open(BACKUP_PATH, encoding="utf-8-sig", newline="") as f:
        backup_reader = csv.DictReader(f)

        if backup_reader.fieldnames != ["text", "intent"]:
            raise ValueError("Backup CSV has unexpected columns.")

        backup_rows = list(backup_reader)

    if original_rows != backup_rows:
        raise ValueError(
            "Current dataset differs from the original backup. "
            "No changes made. Restore the original CSV from the backup first."
        )

    expected_original = {
        "product_issue": 50,
        "account_issue": 50,
        "payment_issue": 50,
        "delivery_issue": 65,
        "cancellation_request": 65,
        "refund_request": 65,
        "general_enquiry": 50,
        "login_issue": 50,
    }

    original_counts = Counter(
        row["intent"] for row in original_rows
    )

    if dict(original_counts) != expected_original:
        raise ValueError(
            f"Unexpected original category counts: {dict(original_counts)}. "
            "No CSV file was modified."
        )

    seen = {
        (row["intent"], normalize(row["text"]))
        for row in original_rows
    }

    all_examples = []

    required_existing = {
        "product_issue": 50,
        "account_issue": 50,
        "payment_issue": 50,
        "delivery_issue": 35,
        "cancellation_request": 35,
        "refund_request": 35,
        "general_enquiry": 50,
        "login_issue": 50,
    }

    if set(EXISTING_ADDITIONS) != set(required_existing):
        raise ValueError(
            "EXISTING_ADDITIONS categories do not match expected categories."
        )

    for intent, required in required_existing.items():

        add_unique_examples(
            all_examples,
            intent,
            EXISTING_ADDITIONS[intent],
            required,
            seen
        )

    new_categories = [
        "return_request",
        "order_status_enquiry",
        "exchange_request",
        "warranty_request",
    ]

    for intent in new_categories:

        if intent not in EXAMPLES:
            raise ValueError(
                f"Missing seed examples for {intent}."
            )

        add_unique_examples(
            all_examples,
            intent,
            EXAMPLES[intent],
            100,
            seen
        )

    expected_final = {
        intent: 100
        for intent in [
            "product_issue",
            "account_issue",
            "payment_issue",
            "delivery_issue",
            "cancellation_request",
            "refund_request",
            "general_enquiry",
            "login_issue",
            "return_request",
            "order_status_enquiry",
            "exchange_request",
            "warranty_request",
        ]
    }

    combined = original_rows + all_examples

    final_counts = Counter(
        row["intent"] for row in combined
    )

    if dict(final_counts) != expected_final or len(combined) != 1200:
        raise ValueError(
            f"Final validation failed: rows={len(combined)}, "
            f"counts={dict(final_counts)}. "
            "No CSV file was modified."
        )

    final_seen = set()

    for row in combined:

        key = (
            row["intent"],
            normalize(row["text"])
        )

        if key in final_seen:
            raise ValueError(
                f"Duplicate message detected: {row['text']}. "
                "No CSV file was modified."
            )

        final_seen.add(key)

    random.shuffle(combined)

    temp_path = CSV_PATH.with_suffix(".tmp")

    try:

        with open(temp_path, "w", encoding="utf-8", newline="") as f:

            writer = csv.DictWriter(
                f,
                fieldnames=["text", "intent"]
            )

            writer.writeheader()
            writer.writerows(combined)

        temp_path.replace(CSV_PATH)

    finally:

        if temp_path.exists():
            temp_path.unlink()

    print("\nDATASET EXPANSION SUCCESSFUL")
    print("=" * 45)

    for intent, count in sorted(final_counts.items()):
        print(f"{intent:<25} {count}")

    print("=" * 45)

    print("Total examples:", len(combined))
    print("Unique messages:", len(final_seen))
    print("Dataset saved:", CSV_PATH)

    print(
        "\nNote: Some wording variants were generated to replace duplicates "
        "and reach 100 examples in each new category."
    )

    print(
        "Review these before using the dataset for a final model-quality evaluation."
    )


if __name__ == "__main__":
    main()