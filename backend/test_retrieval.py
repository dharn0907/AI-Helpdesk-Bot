
from services.ticket_retrieval_service import retrieve_solution

test_messages = [
    ("I am still waiting for my order", "delivery_issue"),
    ("My account password is forgotten", "login_issue"),
    ("I have a completely different problem", "delivery_issue")
]

for message, intent in test_messages:

    print("\nCustomer:", message)

    result = retrieve_solution(message, intent)

    if result:
        print("Match found!")
        print("Ticket ID:", result["ticket_id"])
        print("Previous problem:", result["problem"])
        print("Solution:", result["solution"])
        print("Similarity:", result["similarity"])
    else:
        print("No reliable historical solution found.")
