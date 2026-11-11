
import pandas as pd
from pathlib import Path

DATASET_PATH = Path("data/intent_dataset.csv")

new_examples = [
    # DELIVERY ISSUE
    ("My parcel is still not delivered.", "delivery_issue"),
    ("The delivery date has passed but my order is missing.", "delivery_issue"),
    ("Why is my shipment taking so long?", "delivery_issue"),
    ("My package is stuck in transit.", "delivery_issue"),
    ("The tracking information has not changed.", "delivery_issue"),
    ("I have not received my order yet.", "delivery_issue"),
    ("The courier has not delivered my parcel.", "delivery_issue"),
    ("My order shows delivered but I never received it.", "delivery_issue"),
    ("Where is my package? It is overdue.", "delivery_issue"),
    ("The delivery person did not come to my address.", "delivery_issue"),
    ("My shipment has been delayed again.", "delivery_issue"),
    ("I am still waiting for my parcel.", "delivery_issue"),
    ("The courier service failed to deliver my order.", "delivery_issue"),
    ("My package has been missing for several days.", "delivery_issue"),
    ("Can you check why my order has not arrived?", "delivery_issue"),

    # REFUND REQUEST
    ("I want my money back.", "refund_request"),
    ("Please return the amount I paid.", "refund_request"),
    ("When will I receive my money back?", "refund_request"),
    ("The money has not been credited to my account.", "refund_request"),
    ("I am waiting for my returned payment.", "refund_request"),
    ("I cancelled my order but have not received my money.", "refund_request"),
    ("Please process my repayment.", "refund_request"),
    ("The refund amount is missing from my bank account.", "refund_request"),
    ("I need a reimbursement for this purchase.", "refund_request"),
    ("Why is my refund taking so long?", "refund_request"),
    ("My returned money has not arrived.", "refund_request"),
    ("I have not received the amount for my returned product.", "refund_request"),
    ("Please check the status of my money return.", "refund_request"),
    ("I was promised a refund but nothing was credited.", "refund_request"),
    ("How long does it take to get my money back?", "refund_request"),

    # CANCELLATION REQUEST
    ("I no longer want this order.", "cancellation_request"),
    ("Please stop processing my purchase.", "cancellation_request"),
    ("I placed the order by mistake and want to withdraw it.", "cancellation_request"),
    ("Do not ship my order. I want to cancel it.", "cancellation_request"),
    ("I changed my mind about buying this product.", "cancellation_request"),
    ("Please terminate my subscription.", "cancellation_request"),
    ("I do not want the upcoming renewal.", "cancellation_request"),
    ("Can you stop my order before it is dispatched?", "cancellation_request"),
    ("I want to withdraw my booking.", "cancellation_request"),
    ("Please discontinue my service.", "cancellation_request"),
    ("I accidentally ordered the wrong item. Please cancel it.", "cancellation_request"),
    ("I want to stop this purchase.", "cancellation_request"),
    ("Please remove my order from processing.", "cancellation_request"),
    ("I do not need this booking anymore.", "cancellation_request"),
    ("Cancel my subscription before the next billing date.", "cancellation_request"),
]

df = pd.read_csv(DATASET_PATH)

new_df = pd.DataFrame(new_examples, columns=["text", "intent"])

# Avoid adding exact duplicate examples
existing_texts = set(df["text"].str.strip().str.lower())

new_df = new_df[
    ~new_df["text"].str.strip().str.lower().isin(existing_texts)
]

df = pd.concat([df, new_df], ignore_index=True)

df.to_csv(DATASET_PATH, index=False)

print("New examples added:", len(new_df))
print("\nUpdated category counts:")
print(df["intent"].value_counts())
print("\nTotal examples:", len(df))
