Adaptive ticket investigation update

Replace these files in your project:
backend/main.py
backend/services/llm_service.py
backend/services/ticket_conversation_service.py

These changes pass the active company configuration into ticket investigation and strengthen the Gemini prompts for domain-adaptive issue investigation. Questions are complaint-specific, one at a time, and stop once the issue is actionable. No fixed industry checklist is imposed.

Before replacing, back up your current three files.
