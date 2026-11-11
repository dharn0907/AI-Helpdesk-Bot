
from services.ticket_retrieval_service import (
    model,
    knowledge_base,
    complaint_embeddings
)

from sklearn.metrics.pairwise import cosine_similarity

test_message = "I am still waiting for my order"
test_intent = "delivery_issue"

user_embedding = model.encode([test_message])

scores = cosine_similarity(
    user_embedding,
    complaint_embeddings
)[0]

print("\nCustomer complaint:", test_message)
print("\nSimilarity scores for delivery tickets:\n")

for i, ticket in enumerate(knowledge_base):

    if ticket["intent"] == test_intent:
        print("Ticket ID:", ticket["id"])
        print("Problem:", ticket["problem"])
        print("Similarity:", round(float(scores[i]), 4))
        print("-" * 40)
