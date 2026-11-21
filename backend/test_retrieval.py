from services.ticket_retrieval_service import retrieve_approved_solution

query = """
Login issue: customer enters correct email and password,
but receives invalid credentials error. Tried password reset,
different browser and device. Using mobile browser.
"""

result = retrieve_approved_solution(
    user_message=query,
    intent="login_issue"
)

print("\nRETRIEVAL RESULT:")
print(result)
