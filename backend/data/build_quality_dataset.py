import csv
import re
from pathlib import Path
from collections import Counter

# ==========================================
# DATASET CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

SOURCE_PATH = BASE_DIR / "intent_dataset_backup_8_categories.csv"

OUTPUT_PATH = BASE_DIR / "intent_dataset_quality.csv"

EXPECTED_INTENTS = [
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

TARGET_PER_INTENT = 100
EXPECTED_TOTAL = 1200


# ==========================================
# TEXT NORMALIZATION
# ==========================================

def normalize(text):
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


# ==========================================
# DATASET VALIDATION
# ==========================================

def validate_dataset(rows):

    errors = []

    counts = Counter(
        row["intent"] for row in rows
    )

    if len(rows) != EXPECTED_TOTAL:
        errors.append(
            f"Expected {EXPECTED_TOTAL} rows, found {len(rows)}"
        )

    for intent in EXPECTED_INTENTS:

        if counts[intent] != TARGET_PER_INTENT:
            errors.append(
                f"{intent}: expected 100, found {counts[intent]}"
            )

    unknown = set(counts) - set(EXPECTED_INTENTS)

    if unknown:
        errors.append(
            f"Unknown intents found: {unknown}"
        )

    seen = set()

    for row in rows:

        text = row["text"]
        intent = row["intent"]

        if not text.strip():
            errors.append("Empty message found")
            continue

        key = normalize(text)

        if key in seen:
            errors.append(
                f"Duplicate message found: {text}"
            )
        else:
            seen.add(key)

        if intent not in EXPECTED_INTENTS:
            errors.append(
                f"Invalid intent: {intent}"
            )

    if errors:
        print("\nDATASET VALIDATION FAILED")

        for error in errors:
            print("-", error)

        return False

    print("\nDATASET VALIDATION PASSED")
    print("Total examples:", len(rows))
    print("Unique messages:", len(seen))

    for intent in EXPECTED_INTENTS:
        print(f"{intent:<25} {counts[intent]}")

    return True


# ==========================================
# DATASET WRITING
# ==========================================

def save_dataset(rows):

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=["text", "intent"]
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\nDataset saved:", OUTPUT_PATH)
    # ==========================================
# RETURN REQUEST EXAMPLES
# ==========================================

RETURN_EXAMPLES = [
    "I want to send the laptop back.",
    "The laptop I bought is not suitable for my needs.",
    "I would like to return my recent purchase.",
    "Can I send back a product after receiving it?",
    "I am unhappy with this product and want to return it.",
    "Please tell me how to start a return.",
    "I no longer need the item I purchased.",
    "Can someone arrange a return pickup?",
    "I want to give back the product I ordered.",
    "The item does not match my requirements.",
    "I received my order and would like to return it.",
    "How do I initiate a return for this laptop?",
    "I want to send the product back to your store.",
    "Can I return a product that I have opened?",
    "I changed my mind after receiving the laptop.",
    "The product is not what I expected, so I want to return it.",
    "I need to request a return for my order.",
    "Please explain how I can send this item back.",
    "I want to return the laptop instead of keeping it.",
    "Is it possible to return my recently delivered order?",
    "I would prefer to give the product back.",
    "Can you help me arrange a product return?",
    "I am requesting a return for the item I received.",
    "The laptop does not meet my expectations.",
    "Where can I submit a product return request?",
    "I want to return the item before the return period ends.",
    "Please arrange collection of the product from my address.",
    "I purchased the wrong product and want to return it.",
    "I don't want to keep this item anymore.",
    "Can I send my delivered product back for a return?",
    "I need information about returning a purchased laptop.",
    "The product is unsuitable for me. I want to return it.",
    "How can I hand over the item for a return?",
    "I would like to give back my recent order.",
    "Please help me start the product return procedure.",
    "I want to return this purchase within the allowed period.",
    "Can the courier collect my returned item?",
    "I received the product but decided not to keep it.",
    "I need to know whether my purchase qualifies for a return.",
    "Can I request a return after opening the package?",
    "I want to send the delivered item back to the seller.",
    "Please guide me on returning this laptop.",
    "The product is not right for me, and I want to return it.",
    "I would like to request a pickup for my return.",
    "How do I give back an item I purchased online?",
    "I am looking to return my recently delivered laptop.",
    "Can you start a return request for this product?",
    "I want to return the item rather than exchange it.",
    "Please let me know how to return my purchase.",
    "I have decided not to keep the product and want to return it."
]
# ==========================================
# ORDER STATUS ENQUIRY EXAMPLES
# ==========================================

ORDER_STATUS_EXAMPLES = [
    "Where is my order currently?",
    "Has my purchase been confirmed?",
    "Can you check whether my order is processing?",
    "When is my laptop expected to be dispatched?",
    "I would like an update on my order status.",
    "Has my package been packed yet?",
    "Can you tell me the current order progress?",
    "Is my order confirmed or still pending?",
    "Where can I find the tracking details?",
    "Has the seller started processing my order?",
    "When should I expect the shipping confirmation?",
    "I placed an order yesterday. Is it confirmed?",
    "Can you check if my order has been shipped?",
    "What stage is my purchase currently at?",
    "Has my order moved to the dispatch stage?",
    "I need the latest update about my purchase.",
    "Can I know the estimated dispatch date?",
    "Is my laptop order being prepared?",
    "Has the package left the warehouse?",
    "Can you provide my order tracking information?",
    "I want to know whether my order is packed.",
    "Has my order confirmation been generated?",
    "Can you verify that my purchase was registered?",
    "What is happening with the order I placed?",
    "Is my order waiting for processing?",
    "When will the tracking number become available?",
    "I haven't received an order confirmation yet. Was it placed?",
    "Can you check the progress of my recent purchase?",
    "Has my package been handed to the courier?",
    "Is the order still being prepared for shipment?",
    "Please check the current status of my purchase.",
    "When can I expect my order to leave the warehouse?",
    "I need to know if my order has been dispatched.",
    "Can you confirm whether my order is in the system?",
    "What is the expected shipping date for my laptop?",
    "Has the shipping process started for my order?",
    "Can I get an update on my order confirmation?",
    "Is my purchase still awaiting seller confirmation?",
    "Where can I view the progress of my order?",
    "Can you tell me if my package is ready for shipping?",
    "I want to check the status of my latest order.",
    "Has my order reached the packing stage?",
    "When should I receive the dispatch notification?",
    "Can you verify the shipping status of my purchase?",
    "Is my order awaiting payment confirmation?",
    "I need to know whether the seller accepted my order.",
    "Can you tell me the current stage of order processing?",
    "Has my package been assigned a tracking number?",
    "I want to check whether my order is confirmed.",
    "Please provide the latest information about my order."
]
# ==========================================
# EXCHANGE REQUEST EXAMPLES
# ==========================================

EXCHANGE_EXAMPLES = [
    "I want to exchange my laptop for another model.",
    "Can I swap this laptop for a different configuration?",
    "I received the wrong variant and need an exchange.",
    "I would like a different colour of the same product.",
    "Can I replace my current laptop with another model?",
    "I want to exchange this item for a higher specification.",
    "How do I request an exchange?",
    "I ordered the wrong model. Can I swap it?",
    "Please arrange an exchange for my purchase.",
    "I prefer another variant instead of the one delivered.",
    "Can I exchange my laptop for a model with more RAM?",
    "I need the same product in a different size.",
    "Is it possible to exchange my purchase?",
    "I want a different configuration instead of this one.",
    "Can you help me swap this product?",
    "I would like to exchange the item I received yesterday.",
    "I selected the wrong colour and want another one.",
    "Can I get a different model in exchange?",
    "I want to replace this product with a newer version.",
    "Please tell me the steps for exchanging my laptop.",
    "Can I exchange this laptop for one with a larger SSD?",
    "I need to switch to a different product variant.",
    "The model I received is not the one I wanted. I need an exchange.",
    "I would prefer another laptop from your catalogue.",
    "Can I exchange my purchase rather than return it?",
    "I want to swap my current item for a different one.",
    "Please change my product to another available model.",
    "I need an exchange because I chose the wrong specification.",
    "Can the delivered product be exchanged for another variant?",
    "I would like a replacement with a different configuration.",
    "Is there an option to exchange this item?",
    "I want to change my laptop to a higher-end model.",
    "Can I switch my order to another available colour?",
    "Please help me exchange the product I purchased.",
    "I need a different size and want to exchange this one.",
    "Can I get another model instead of this laptop?",
    "I would like to trade this product for a different version.",
    "How long does it take to complete an exchange?",
    "Can you arrange pickup and delivery for an exchange?",
    "I want to exchange the item for the same model in another colour.",
    "My current configuration is insufficient. Can I exchange it?",
    "I received a variant I did not select. Please arrange an exchange.",
    "Can I upgrade my laptop through an exchange?",
    "I want to switch to a model with a better graphics card.",
    "Please explain your product exchange procedure.",
    "I would like to exchange this purchase for another product.",
    "Can I request an exchange for a different specification?",
    "I need to replace the delivered model with the one I intended to buy.",
    "Can you change the product I received to another variant?",
    "I would rather exchange this item than keep it."
]# ==========================================
# WARRANTY REQUEST EXAMPLES
# ==========================================

WARRANTY_EXAMPLES = [
    "Is my laptop still covered by its warranty?",
    "How can I register a warranty claim?",
    "What is the warranty period for this device?",
    "I need to get my laptop repaired under warranty.",
    "Does my product qualify for warranty service?",
    "Can you check the warranty status of my laptop?",
    "Where can I submit a warranty claim?",
    "I want to know when my product warranty expires.",
    "Does the warranty cover battery problems?",
    "How do I contact an authorized warranty centre?",
    "My laptop has a hardware fault. Can I claim warranty?",
    "Is accidental damage included in the warranty?",
    "Can I get a free repair under the manufacturer's warranty?",
    "How long is the warranty valid after purchase?",
    "I need help understanding my warranty coverage.",
    "Can I claim warranty service for a faulty keyboard?",
    "Does my laptop warranty cover the display?",
    "I want to verify whether my device is still under warranty.",
    "What documents are required for a warranty claim?",
    "Can you explain the warranty registration process?",
    "My laptop stopped working during the warranty period.",
    "How do I request an authorized warranty repair?",
    "Is the charger included in the product warranty?",
    "I need the contact details of the warranty service provider.",
    "Can the battery be replaced under warranty?",
    "Does the warranty cover manufacturing defects?",
    "My laptop is malfunctioning. Is it eligible for warranty repair?",
    "How can I find the warranty expiry date?",
    "I want to register my newly purchased laptop for warranty.",
    "Can I get warranty support for my product?",
    "Does the warranty cover motherboard failures?",
    "Where can I take my device for warranty service?",
    "Is there an international warranty for this laptop?",
    "Can I extend the warranty period for my purchase?",
    "My product developed a fault within the warranty period.",
    "What is the procedure for claiming manufacturer warranty?",
    "I need to check whether my laptop has an active warranty.",
    "Does the warranty cover problems with the screen?",
    "Can I request a warranty replacement for a defective device?",
    "How do I track my existing warranty claim?",
    "Is physical damage covered by the standard warranty?",
    "My warranty claim was rejected. Can you explain why?",
    "Can I transfer the warranty to another owner?",
    "Does opening the laptop affect its warranty?",
    "I want to know the terms of my product warranty.",
    "Where can I check the warranty details for my purchase?",
    "Can I get service at a different authorized service centre?",
    "How do I claim warranty support for a faulty processor?",
    "Is my laptop eligible for a warranty extension?",
    "Please explain how warranty repairs are handled."
]
# ==========================================
# ADDITIONAL RETURN REQUEST EXAMPLES
# ==========================================

RETURN_EXTRA_EXAMPLES = [
    "The laptop I received is not suitable, and I want to send it back.",
    "I would like to return my order and get a refund.",
    "Can you explain the conditions for returning a delivered item?",
    "I bought this laptop by mistake and want to give it back.",
    "Please initiate the return process for my purchase.",
    "I am not satisfied with the product and would like to return it.",
    "Can a return be arranged for an item purchased online?",
    "I want to send the laptop back to the seller.",
    "The product does not suit my requirements. Can I return it?",
    "I need to know the last date for returning my purchase.",
    "I would like to withdraw from this purchase and return the item.",
    "Can you provide instructions for sending back my order?",
    "I have received the item but no longer wish to keep it.",
    "Please help me submit a request to return this product.",
    "Is home pickup available for returned products?",
    "I want to return the laptop I received last week.",
    "Can I return an item if I have already opened its box?",
    "I would like to know the return process for my purchase.",
    "The product is unsuitable, so I have decided to send it back.",
    "Can you schedule a collection for the item I want to return?",
    "I need to return my recently purchased computer.",
    "How can I hand over my product for a return?",
    "I don't wish to retain this purchase. I want to return it.",
    "Can you help me with the return formalities?",
    "I want to send this product back within the return window.",
    "Please initiate a return for the laptop delivered to me.",
    "I would like to know if my order is eligible for return.",
    "Can I return a product without its original packaging?",
    "I have decided to return the item instead of keeping it.",
    "What should I do to send my purchased laptop back?",
    "I need assistance with the return of my delivered product.",
    "Can you arrange a courier to collect my return?",
    "I want to give back the laptop I ordered online.",
    "The item I purchased is not useful to me. I want to return it.",
    "Please tell me how to request a return pickup.",
    "I would like to return my purchase before the deadline.",
    "Is there a way to return an unwanted product?",
    "I received the laptop but want to send it back to your store.",
    "Can you guide me through the steps to return this item?",
    "I want to request a return for the product delivered to my address.",
    "I no longer want this purchase and would like to return it.",
    "How do I arrange the collection of a product I am returning?",
    "I need to know the procedure for returning an online order.",
    "Can this laptop be returned after delivery?",
    "I want to return the product because I selected the wrong item.",
    "Please let me know how to hand over my unwanted purchase.",
    "I would like to start the return process for my delivered order.",
    "Can you confirm whether I can send this product back?",
    "I am planning to return the laptop I purchased.",
    "Please explain how I can return an item bought from your store."
]
# ==========================================
# ADDITIONAL ORDER STATUS EXAMPLES
# ==========================================

ORDER_STATUS_EXTRA_EXAMPLES = [
    "Could you tell me whether my order has been accepted?",
    "I placed an order a few hours ago. Can I check its status?",
    "Has my order been confirmed by the store?",
    "Where can I see the current progress of my laptop order?",
    "Is my purchase still being processed?",
    "When will the order details appear in my account?",
    "Can you check whether a tracking ID has been generated?",
    "I need to know the estimated delivery date shown for my order.",
    "Has the warehouse received my order request?",
    "Can I get the latest update on my shipment?",
    "Is my order ready to be sent out?",
    "Has the courier been assigned to my package?",
    "Can you confirm the status of the order I placed today?",
    "I want to know whether my payment and order are confirmed.",
    "When will I receive the shipping details?",
    "Is my order still awaiting confirmation?",
    "Can you tell me the expected date of dispatch?",
    "Has my package been collected by the delivery company?",
    "Where can I check my order history and status?",
    "Can you verify whether my laptop order was successfully placed?",
    "I would like to see the latest update for my purchase.",
    "Has my order been moved to shipment processing?",
    "Can you check if the seller has confirmed my purchase?",
    "What is the current stage of my order?",
    "When will my order tracking link be activated?",
    "Is the package still at the warehouse?",
    "Can you provide an update on the order I placed last night?",
    "Has my purchase been assigned an order number?",
    "I want to confirm that my order is registered successfully.",
    "Can you tell me whether the package is ready for dispatch?",
    "What is the estimated arrival date for my order?",
    "Has my shipment been handed over to the courier?",
    "Can I check whether my order has entered transit?",
    "I haven't received a dispatch message. Has my order shipped?",
    "Where can I find the latest information about my purchase?",
    "Has the seller processed my laptop order?",
    "Can you check whether my package has been packed?",
    "Is there an update on the order confirmation?",
    "When will the tracking number be shared with me?",
    "I need to verify the status of my recent transaction order.",
    "Has my order moved beyond the confirmation stage?",
    "Can you tell me if my purchase is ready for shipment?",
    "I would like to check the progress of an existing order.",
    "Is my order currently with the delivery partner?",
    "Can you confirm the expected dispatch date for my purchase?",
    "Has the system generated a confirmation for my order?",
    "Where can I view the tracking status of my package?",
    "Can you check whether my order is still being prepared?",
    "I want an update on the shipment of my laptop.",
    "Please check the current processing status of my order."
]# ==========================================
# ADDITIONAL EXCHANGE REQUEST EXAMPLES
# ==========================================

EXCHANGE_EXTRA_EXAMPLES = [
    "I would like to swap my laptop for a different brand.",
    "Can I exchange this model for one with a better processor?",
    "The laptop I received has the wrong specifications. I need another one.",
    "I want to change my purchase to a different laptop model.",
    "Can you exchange my current product for a higher RAM variant?",
    "I selected the wrong configuration and want to switch it.",
    "Please replace this model with the variant I originally wanted.",
    "I would like to exchange my laptop for a lighter model.",
    "Can I swap my purchase for a laptop with a dedicated GPU?",
    "I need to exchange this product for a different colour option.",
    "Can I change the delivered model to one with a larger display?",
    "I want another variant instead of the laptop I received.",
    "Please help me switch my purchase to a different configuration.",
    "Is an exchange possible if I want a more powerful model?",
    "I would like to trade my current laptop for another available model.",
    "Can you arrange an exchange for the incorrect variant?",
    "I want to change my laptop to a model with more storage.",
    "The configuration I ordered is not what I need. Can I exchange it?",
    "Can I swap this product for a different item of similar value?",
    "I would prefer a laptop with a different processor. Can I exchange mine?",
    "Please change my current product to the model I selected earlier.",
    "I need to exchange the item for a version with better specifications.",
    "Can I get a different model through your exchange process?",
    "I want to switch from this laptop to another model in your store.",
    "Can the product be exchanged for a different brand?",
    "I received the wrong colour and want the correct one.",
    "I would like to exchange my purchase for a model with more memory.",
    "Please arrange a swap for the laptop delivered to me.",
    "Can I exchange this product for a newer generation model?",
    "I want a different configuration from the one currently delivered.",
    "Is it possible to switch to another laptop after delivery?",
    "I need to replace my current variant with a different specification.",
    "Can I exchange my laptop for one with a better graphics card?",
    "I ordered the base model but would prefer the upgraded version.",
    "Please help me change the product variant I received.",
    "I want to exchange this laptop for a model with a larger screen.",
    "Can you tell me how to switch to another available product?",
    "I would like a different model instead of the one delivered.",
    "Can I exchange my current purchase for a higher-priced variant?",
    "I need to swap this item for the correct model.",
    "The selected product variant is unsuitable. I want to exchange it.",
    "Can I change the laptop configuration through an exchange request?",
    "I want to trade my existing product for another version.",
    "Please arrange an exchange for a laptop with a different processor.",
    "I would prefer another model from your available collection.",
    "Can I switch to a laptop with a larger SSD?",
    "I want to exchange the delivered product for the model I intended to buy.",
    "Is there an option to change my product to another variant?",
    "I need a different laptop model and would like to exchange this one.",
    "Please guide me through exchanging my current product."
]# ==========================================
# ADDITIONAL WARRANTY REQUEST EXAMPLES
# ==========================================

WARRANTY_EXTRA_EXAMPLES = [
    "My laptop is still under warranty. How can I get it serviced?",
    "Can you verify the warranty using my serial number?",
    "I need to know if the motherboard is covered by warranty.",
    "How can I raise a service request under warranty?",
    "My laptop warranty is about to expire. What should I do?",
    "Can I get a warranty repair for a faulty charging port?",
    "Does the manufacturer provide onsite warranty service?",
    "I purchased an extended warranty. How can I use it?",
    "Where can I find the warranty certificate for my laptop?",
    "My warranty registration is not showing up. Can you check it?",
    "Can I claim warranty for a laptop that suddenly stopped booting?",
    "What is the process for checking warranty coverage?",
    "I need to submit my invoice for a warranty claim.",
    "Does the warranty cover defects in the laptop's speakers?",
    "Can I get my faulty touchpad repaired under warranty?",
    "How do I book a warranty service appointment?",
    "My laptop has a manufacturing defect. How can I claim warranty?",
    "Can you tell me whether the adapter is covered by warranty?",
    "I want to know the warranty terms for my purchased device.",
    "Is the laptop eligible for warranty service at any service centre?",
    "How can I check the remaining warranty period?",
    "My warranty claim is still pending. Can I get an update?",
    "Can the service centre verify my device's warranty?",
    "I need to know if liquid damage is covered under my warranty.",
    "Does the warranty include replacement of a defective screen?",
    "How do I register my device for manufacturer warranty?",
    "Can I request warranty service if the laptop overheats?",
    "My laptop is within the warranty period, but the service centre refused repair.",
    "Where should I submit my laptop for warranty inspection?",
    "Does the warranty cover a faulty cooling fan?",
    "I need to extend the warranty on my existing laptop.",
    "Can you help me understand why my warranty claim was declined?",
    "What information is needed to verify my warranty?",
    "My laptop's motherboard failed. Can it be repaired under warranty?",
    "Is the keyboard covered if some keys stop responding?",
    "Can I transfer my warranty when selling the laptop?",
    "I want to know whether my warranty is active.",
    "How can I get a warranty replacement for a defective charger?",
    "Does my device have international warranty coverage?",
    "Can I claim warranty without the original box?",
    "My laptop display has developed lines. Is this covered?",
    "How do I find an authorized centre for warranty repairs?",
    "Can you check whether my warranty registration was successful?",
    "I need help with an existing manufacturer warranty claim.",
    "Will the warranty cover a laptop that fails to power on?",
    "Can I get the battery checked under the warranty?",
    "What happens if my laptop develops a fault during the warranty period?",
    "I need to know how long warranty repairs usually take.",
    "Can I request a warranty inspection for my device?",
    "Please guide me through claiming the warranty on my laptop."
]# ==========================================
# ADDITIONAL PRODUCT ISSUE EXAMPLES
# ==========================================

PRODUCT_EXTRA_EXAMPLES = [
    "My laptop screen keeps flickering while I use it.",
    "The keyboard on my new laptop is not responding.",
    "My laptop shuts down unexpectedly during normal use.",
    "The touchpad is not detecting my finger movements.",
    "My laptop battery drains very quickly.",
    "The charging port seems loose and does not connect properly.",
    "My laptop is making an unusual buzzing noise.",
    "The display has developed a bright spot.",
    "Several keys on my keyboard have stopped working.",
    "My laptop gets extremely hot even when I open simple applications.",
    "The speakers produce distorted sound.",
    "My laptop is stuck on the startup screen.",
    "The webcam is not working on my device.",
    "My laptop restarts randomly without warning.",
    "The power button does not respond consistently.",
    "My screen goes black after a few minutes.",
    "The laptop fan is unusually loud.",
    "My device does not recognize the USB ports.",
    "The hinge on my laptop feels loose.",
    "My laptop is running much slower than it used to.",
    "The Wi-Fi adapter keeps disconnecting on this laptop.",
    "My laptop battery is not charging beyond a certain percentage.",
    "The trackpad sometimes freezes while I am typing.",
    "I noticed dead pixels on the laptop display.",
    "My laptop produces no sound through its built-in speakers.",
    "The fingerprint reader is not recognizing my finger.",
    "My laptop freezes whenever I launch a demanding application.",
    "The screen brightness keeps changing on its own.",
    "My laptop cannot detect the installed SSD.",
    "The charger gets unusually hot when connected.",
    "My laptop has a cracked screen.",
    "The keyboard backlight has stopped illuminating.",
    "My laptop does not turn on even when plugged in.",
    "The display keeps flickering when I adjust the screen angle.",
    "My device is overheating while charging.",
    "The audio jack is not detecting my headphones.",
    "My laptop fan does not seem to spin.",
    "The webcam image is blurry even after cleaning the lens.",
    "My laptop keeps showing blue screen errors.",
    "The battery percentage suddenly drops while I am working.",
    "The screen has visible lines across it.",
    "My laptop is unable to detect an external monitor.",
    "The power adapter connection keeps cutting out.",
    "My laptop keyboard types different characters than expected.",
    "The laptop casing is making a clicking sound near the hinge.",
    "My device crashes whenever I connect a USB drive.",
    "The built-in microphone is not picking up my voice.",
    "My laptop takes a very long time to boot.",
    "The display colour looks distorted on my laptop.",
    "My laptop is experiencing frequent hardware freezes."
]# ==========================================
# ADDITIONAL PRODUCT ISSUE EXAMPLES
# ==========================================

PRODUCT_EXTRA_EXAMPLES = [
    "My laptop screen keeps flickering while I use it.",
    "The keyboard on my new laptop is not responding.",
    "My laptop shuts down unexpectedly during normal use.",
    "The touchpad is not detecting my finger movements.",
    "My laptop battery drains very quickly.",
    "The charging port seems loose and does not connect properly.",
    "My laptop is making an unusual buzzing noise.",
    "The display has developed a bright spot.",
    "Several keys on my keyboard have stopped working.",
    "My laptop gets extremely hot even when I open simple applications.",
    "The speakers produce distorted sound.",
    "My laptop is stuck on the startup screen.",
    "The webcam is not working on my device.",
    "My laptop restarts randomly without warning.",
    "The power button does not respond consistently.",
    "My screen goes black after a few minutes.",
    "The laptop fan is unusually loud.",
    "My device does not recognize the USB ports.",
    "The hinge on my laptop feels loose.",
    "My laptop is running much slower than it used to.",
    "The Wi-Fi adapter keeps disconnecting on this laptop.",
    "My laptop battery is not charging beyond a certain percentage.",
    "The trackpad sometimes freezes while I am typing.",
    "I noticed dead pixels on the laptop display.",
    "My laptop produces no sound through its built-in speakers.",
    "The fingerprint reader is not recognizing my finger.",
    "My laptop freezes whenever I launch a demanding application.",
    "The screen brightness keeps changing on its own.",
    "My laptop cannot detect the installed SSD.",
    "The charger gets unusually hot when connected.",
    "My laptop has a cracked screen.",
    "The keyboard backlight has stopped illuminating.",
    "My laptop does not turn on even when plugged in.",
    "The display keeps flickering when I adjust the screen angle.",
    "My device is overheating while charging.",
    "The audio jack is not detecting my headphones.",
    "My laptop fan does not seem to spin.",
    "The webcam image is blurry even after cleaning the lens.",
    "My laptop keeps showing blue screen errors.",
    "The battery percentage suddenly drops while I am working.",
    "The screen has visible lines across it.",
    "My laptop is unable to detect an external monitor.",
    "The power adapter connection keeps cutting out.",
    "My laptop keyboard types different characters than expected.",
    "The laptop casing is making a clicking sound near the hinge.",
    "My device crashes whenever I connect a USB drive.",
    "The built-in microphone is not picking up my voice.",
    "My laptop takes a very long time to boot.",
    "The display colour looks distorted on my laptop.",
    "My laptop is experiencing frequent hardware freezes."
]# ==========================================
# ADDITIONAL PAYMENT ISSUE EXAMPLES
# ==========================================

PAYMENT_EXTRA_EXAMPLES = [
    "My UPI payment failed but the amount was deducted.",
    "The payment page froze after I entered my card details.",
    "I was charged twice for the same order.",
    "My bank shows a successful transaction, but your website shows payment pending.",
    "The payment gateway is not accepting my debit card.",
    "I cannot complete the payment using net banking.",
    "Money was deducted, but I did not receive a payment confirmation.",
    "My transaction failed while processing the order.",
    "The website keeps declining my valid credit card.",
    "I paid for my order, but the payment status has not changed.",
    "The UPI app says payment successful, but the order remains unpaid.",
    "My card was charged without the order being created.",
    "I received an error after confirming the payment.",
    "The transaction reference shows success, but your system says failed.",
    "I am unable to pay through the available payment options.",
    "My wallet balance was deducted during checkout.",
    "The payment was debited, but I cannot find the transaction in my order.",
    "I accidentally made two payments for one purchase.",
    "My online banking payment is stuck on processing.",
    "The payment confirmation page never appeared.",
    "I am getting an error whenever I try to pay.",
    "My transaction was cancelled even though the bank approved it.",
    "The payment amount was deducted more than once.",
    "I cannot use my saved card to complete checkout.",
    "The payment is showing as unsuccessful in my account.",
    "My money was debited, but the merchant has not received it.",
    "The payment gateway keeps timing out during checkout.",
    "I received a payment failure message after the amount was deducted.",
    "My card transaction is successful, but the order is not confirmed.",
    "The checkout page is not processing my UPI payment.",
    "I need help with a transaction that is stuck in pending status.",
    "The bank confirmed the debit, but your website has no payment record.",
    "I was charged an incorrect amount during checkout.",
    "My payment keeps getting rejected even though I have sufficient balance.",
    "The transaction was successful but the invoice shows unpaid.",
    "I cannot complete my purchase because the payment service is unavailable.",
    "My account was debited, but the payment status is still failed.",
    "The payment was deducted from my wallet without completing the order.",
    "I received two transaction messages for a single purchase.",
    "The payment page returned an error after processing my card.",
    "My bank transfer has not been reflected in the order.",
    "I am unable to pay using my preferred payment method.",
    "The payment process stops before the transaction is completed.",
    "My card payment was processed but the website did not update.",
    "The amount deducted from my account does not match the checkout total.",
    "I need assistance with a failed transaction.",
    "My payment confirmation is missing even though the money was debited.",
    "The transaction is pending for a long time after checkout.",
    "I paid through net banking, but the order still asks me to pay.",
    "My payment was debited but the purchase was not completed."
]# ==========================================
# ADDITIONAL DELIVERY ISSUE EXAMPLES
# ==========================================

DELIVERY_EXTRA_EXAMPLES = [
    "My package has not arrived on the promised date.",
    "The courier delivered my order to the wrong address.",
    "I received a delivery notification, but no package arrived.",
    "My shipment has been stuck in transit for several days.",
    "The delivery person marked my order delivered, but I did not receive it.",
    "My package arrived with damaged outer packaging.",
    "The courier attempted delivery at an incorrect location.",
    "My order was delivered to someone else.",
    "The delivery address is correct, but the courier cannot locate it.",
    "My shipment has not moved from the dispatch centre.",
    "The package is missing after being handed to the courier.",
    "I received someone else's parcel instead of my order.",
    "The delivery person keeps postponing the delivery.",
    "My laptop shipment is delayed without any explanation.",
    "The courier says delivery was attempted, but nobody contacted me.",
    "My package arrived later than the estimated delivery date.",
    "The parcel was left outside my house without informing me.",
    "The tracking page shows an incorrect delivery location.",
    "My order is showing as out for delivery for two days.",
    "The courier has not delivered my package despite repeated updates.",
    "My parcel was delivered to the wrong apartment.",
    "The shipment tracking has not updated since dispatch.",
    "I received a package with missing items inside.",
    "The delivery agent refused to deliver to my address.",
    "My order was returned to the warehouse without my request.",
    "The courier cannot find my delivery address.",
    "My package is delayed because the delivery partner has not contacted me.",
    "The delivered parcel contains a different product from what I ordered.",
    "My shipment appears lost while in transit.",
    "The delivery status says completed, but I have not received anything.",
    "My package arrived with visible damage caused during shipping.",
    "The courier has repeatedly failed to deliver my order.",
    "My delivery was sent to an old address instead of my current one.",
    "The package has been sitting at the local delivery hub for days.",
    "I have not received my order even though the tracking shows delivered."
]# ==========================================
# ADDITIONAL CANCELLATION REQUEST EXAMPLES
# ==========================================

CANCELLATION_EXTRA_EXAMPLES = [
    "Please cancel the order I placed this morning.",
    "I no longer want to proceed with this purchase.",
    "Can you stop processing my current order?",
    "I would like to withdraw my laptop order.",
    "Please cancel my subscription before the next billing date.",
    "I accidentally placed an order and need it cancelled.",
    "I want to cancel the purchase before it gets dispatched.",
    "Can you terminate my active subscription?",
    "Please stop the shipment and cancel my order.",
    "I have changed my mind and do not want this order anymore.",
    "How can I request cancellation of my recent purchase?",
    "I need to cancel the service I signed up for.",
    "Please withdraw my order from the processing queue.",
    "I selected the wrong item and want to cancel the order.",
    "Can you cancel the order associated with my account?",
    "I don't need the product anymore. Please cancel my purchase.",
    "I want to discontinue my monthly subscription.",
    "Please cancel my order before it is shipped.",
    "I would like to stop my recurring service plan.",
    "Can I cancel an order that has not been dispatched yet?",
    "I need to withdraw the purchase request I submitted.",
    "Please deactivate my paid subscription renewal.",
    "I want to cancel the order I placed by mistake.",
    "The purchase is no longer required. Please cancel it.",
    "Can you stop my subscription from renewing next month?",
    "I would like to cancel my recently placed laptop order.",
    "Please terminate the service linked to my account.",
    "I no longer wish to continue with this order.",
    "Can you remove my pending order from the system?",
    "I want to cancel the product order before delivery.",
    "Please stop the recurring payment plan by cancelling my subscription.",
    "I need to cancel an order that is still being processed.",
    "Can you withdraw my order request?",
    "I have decided not to buy this product. Please cancel the order.",
    "Please cancel my subscription and stop future renewals."
]
# ==========================================
# ADDITIONAL REFUND REQUEST EXAMPLES
# ==========================================

REFUND_EXTRA_EXAMPLES = [
    "My refund has not reached my bank account yet.",
    "I cancelled my purchase but have not received the money back.",
    "Can you check why my refund is still pending?",
    "The refund confirmation was sent, but the amount is missing.",
    "I returned the laptop several days ago. Where is my refund?",
    "My refund was approved but has not been credited.",
    "I received only part of the amount I paid.",
    "The refund was processed to an incorrect payment method.",
    "I want an update on the money being returned for my order.",
    "My bank account has not received the promised refund.",
    "The refund status has not changed since my return was accepted.",
    "How many days will it take for my cancelled order refund?",
    "I have not received the refund for my failed purchase.",
    "The refund amount shown is less than what I originally paid.",
    "Can you verify whether my refund has been initiated?",
    "My returned product was received, but the refund is missing.",
    "I need help tracking the refund for my cancelled order.",
    "The refund was marked completed, but my balance has not increased.",
    "I was told the money would be returned, but nothing has arrived.",
    "Why has my refund not appeared on my credit card statement?",
    "My refund request is approved but the payment has not been reversed.",
    "I need the reference number for my refund transaction.",
    "The refund for my laptop order is taking longer than expected.",
    "Can you investigate the missing refund amount?",
    "My payment was reversed, but the refund is not visible in my account.",
    "I received a refund notification for an amount I cannot find.",
    "The refund has been pending for more than a week.",
    "Please check the progress of my return refund.",
    "I want to know when the refunded amount will be credited.",
    "My cancelled subscription payment has not been refunded.",
    "The refund was sent to my old bank account. How can I resolve this?",
    "I received a partial refund instead of the full amount.",
    "Can you confirm the date on which my refund was processed?",
    "The refund for my returned item is still not credited.",
    "I need assistance because my approved refund has not arrived."
]# ==========================================
# ADDITIONAL GENERAL ENQUIRY EXAMPLES
# ==========================================

GENERAL_EXTRA_EXAMPLES = [
    "What laptop brands are available in your store?",
    "Do you offer student discounts on laptops?",
    "What are your store opening hours?",
    "Can I purchase a laptop through monthly instalments?",
    "Do you sell laptop accessories?",
    "Which payment methods do you accept?",
    "Do you have any ongoing promotional offers?",
    "Can I compare different laptop models on your website?",
    "Do you provide GST invoices for purchases?",
    "What is the minimum order value for free delivery?",
    "Do you offer gift cards?",
    "Can I purchase an extended warranty with a new laptop?",
    "Do you have a physical store where I can see the products?",
    "Which laptop brands do you officially sell?",
    "Do you provide discounts for bulk purchases?",
    "What are the terms of your return policy?",
    "Do you offer cash on delivery?",
    "Can I buy additional RAM for a laptop from your store?",
    "Do you sell refurbished laptops?",
    "Are product specifications listed on your website?",
    "Do you provide installation services?",
    "Can I purchase a laptop as a gift for someone else?",
    "What is the difference between your standard and premium service plans?",
    "Do you have a catalogue of available laptop models?",
    "Are there any additional charges for online orders?",
    "Do you support international shipping?",
    "What documents are needed for a business purchase?",
    "Do you provide student offers during admission season?",
    "Can I use multiple discount coupons on one purchase?",
    "Do you offer discounts during festival sales?",
    "Where can I read your privacy policy?",
    "Do you have a customer support centre?",
    "Can I purchase a laptop without creating an account?",
    "Do you provide product demonstrations?",
    "What brands of gaming laptops do you carry?",
    "Are accessories included with the laptop purchase?",
    "Do you have a loyalty or rewards programme?",
    "Can I get a quotation before placing a bulk order?",
    "Do you offer different delivery options?",
    "What is your policy for damaged products?",
    "Do you provide technical specifications for each model?",
    "Are there any offers for first-time customers?",
    "Can I purchase an extended service plan?",
    "Do you have laptops suitable for programming?",
    "What is the process for placing a bulk order?",
    "Do you provide support for business customers?",
    "Can I browse products by price range?",
    "Where can I find information about your available services?",
    "Do you sell laptop bags and cooling pads?",
    "What are the general terms and conditions for purchases?"
]# ==========================================
# ADDITIONAL LOGIN ISSUE EXAMPLES
# ==========================================

LOGIN_EXTRA_EXAMPLES = [
    "I cannot sign in even though my password is correct.",
    "The website keeps taking me back to the login page.",
    "My OTP is not arriving on my registered mobile number.",
    "I am unable to access my account after entering my credentials.",
    "The login button does not respond when I click it.",
    "My password reset link is not working.",
    "I keep getting an invalid credentials message.",
    "The login page says my session has expired.",
    "I cannot log in using my registered email address.",
    "The verification code expires before I can enter it.",
    "My account login fails whenever I use the mobile app.",
    "I am not receiving the password reset email.",
    "The website rejects my new password during sign-in.",
    "I am stuck on the two-factor authentication screen.",
    "My login attempt is blocked even with the correct OTP.",
    "The sign-in page keeps showing a technical error.",
    "I cannot access my account after changing my password.",
    "The authentication code is not being accepted.",
    "I am unable to log in from a new device.",
    "The login page freezes after I submit my details.",
    "My account keeps asking me to verify my identity.",
    "I cannot sign in because the OTP service is unavailable.",
    "The password recovery process is not sending me a code.",
    "I get redirected to the login screen repeatedly.",
    "My saved login credentials are no longer accepted.",
    "The sign-in process fails after successful OTP verification.",
    "I cannot access the customer portal because login fails.",
    "The system says my password is incorrect every time.",
    "I am unable to complete email verification during login.",
    "My login session ends immediately after signing in.",
    "The authentication page is not loading properly.",
    "I am not getting the verification code needed to log in.",
    "My account will not sign in through the browser.",
    "The login form keeps clearing my entered information.",
    "I cannot reset my password because the link has expired.",
    "The website does not recognize my registered username.",
    "I am having trouble signing in after enabling two-factor authentication.",
    "My OTP verification fails even when I enter the latest code.",
    "The app shows a login error whenever I try to access my account.",
    "I cannot get past the account authentication step.",
    "The password reset code is not being accepted.",
    "My login request keeps timing out.",
    "I am unable to sign in after several password reset attempts.",
    "The system is not recognizing my login credentials.",
    "I cannot complete the sign-in process on my phone.",
    "The verification email for account access never arrives.",
    "My account login is failing after the latest website update.",
    "I am unable to authenticate my account using OTP.",
    "The login page displays an error after I enter my password.",
    "Please help me resolve the sign-in problem."
]# ==========================================
# MAIN DATASET BUILDER
# ==========================================

def main():

    print("Building quality intent dataset...")

    # Read the original 8-category dataset
    with open(
        SOURCE_PATH,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not {"text", "intent"}.issubset(reader.fieldnames or []):
            raise ValueError(
                "Source CSV must contain text and intent columns."
            )

        rows = [
            {
                "text": row["text"].strip(),
                "intent": row["intent"].strip()
            }
            for row in reader
        ]

    print("Original examples loaded:", len(rows))

    # Additional examples for the original 8 categories
    original_additions = {
        "product_issue": PRODUCT_EXTRA_EXAMPLES,
        "account_issue": ACCOUNT_EXTRA_EXAMPLES,
        "payment_issue": PAYMENT_EXTRA_EXAMPLES,
        "delivery_issue": DELIVERY_EXTRA_EXAMPLES,
        "cancellation_request": CANCELLATION_EXTRA_EXAMPLES,
        "refund_request": REFUND_EXTRA_EXAMPLES,
        "general_enquiry": GENERAL_EXTRA_EXAMPLES,
        "login_issue": LOGIN_EXTRA_EXAMPLES,
    }

    # Additional examples for the 4 new categories
    new_category_examples = {
        "return_request": (
            RETURN_EXAMPLES + RETURN_EXTRA_EXAMPLES
        ),
        "order_status_enquiry": (
            ORDER_STATUS_EXAMPLES + ORDER_STATUS_EXTRA_EXAMPLES
        ),
        "exchange_request": (
            EXCHANGE_EXAMPLES + EXCHANGE_EXTRA_EXAMPLES
        ),
        "warranty_request": (
            WARRANTY_EXAMPLES + WARRANTY_EXTRA_EXAMPLES
        ),
    }

    # Add examples to the original categories
    for intent, examples in original_additions.items():

        for example in examples:
            rows.append({
                "text": example,
                "intent": intent
            })

    # Add all examples for the four new categories
    for intent, examples in new_category_examples.items():

        for example in examples:
            rows.append({
                "text": example,
                "intent": intent
            })

    # Shuffle examples reproducibly
    import random
    random.Random(42).shuffle(rows)

    # Validate before saving
    if not validate_dataset(rows):
        print("\nDataset was NOT saved because validation failed.")
        return

    save_dataset(rows)

    print("\nDATASET BUILD COMPLETED")
    print("Output:", OUTPUT_PATH)


if __name__ == "__main__":
    main()