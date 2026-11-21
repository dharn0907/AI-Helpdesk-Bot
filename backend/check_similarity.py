from services.ticket_retrieval_service import model
from sklearn.metrics.pairwise import cosine_similarity

historical = "i have some issues related to login"

new_complaint = """
Login issue: customer enters correct email and password,
but receives invalid credentials error. Tried password reset,
different browser and device. Using mobile browser.
"""

embeddings = model.encode([historical, new_complaint])
score = cosine_similarity([embeddings[1]], [embeddings[0]])[0][0]

print("SIMILARITY SCORE:", round(float(score), 4))
print("CURRENT THRESHOLD: 0.50")
print("MATCH:", score >= 0.50)
