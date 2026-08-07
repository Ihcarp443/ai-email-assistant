from langchain_core.tools import tool
from services.llm import model
from datetime import datetime
import json

@tool
def detect_meeting_intent(email_content: str) -> dict:
    """
    Detect the meeting-related intent in an email.
    """

    prompt = f"""
Analyze the email.

Determine if it is related to a meeting.

Choose intent ONLY from:

- schedule
- invitation
- availability_check
- reschedule
- cancel
- none

Return ONLY JSON.

{{
    "meeting_related": true,
    "meeting_intent": ""
}}

Email:

{email_content}
"""

    response = model.invoke(prompt)

    response = str(response)
    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()

    return json.loads(response)



@tool
def extract_meeting_details(email_content: str) -> dict:
    """
    Extract meeting details from email.
    """

    today = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
Today's date is {today}.

Extract meeting information from the email.

Rules:

1. Normalize date to YYYY-MM-DD.
2. Normalize time to HH:MM (24-hour format).
3. Extract all attendees mentioned.
4. If an attendee email is explicitly mentioned, include it.
5. Do NOT invent email addresses.
6. If only a name is present, keep email as empty string.
7. If meeting information is missing, add the field name in missing_information.

Return ONLY valid JSON.

Format:

{{
    "meeting_date": "",
    "meeting_time": "",
    "duration_minutes": 30,
    "attendees": [
        {{
            "name": "",
            "email": ""
        }}
    ],
    "missing_information": []
}}

Email:

{email_content}
"""
    response = model.invoke(prompt)

    response = str(response)
    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()

    return json.loads(response)

# ----------------------------------------------------
@tool
def extract_action_items(email_content: str) -> dict:
    """
    Extract action items from an email.
    """

    print("\n===== ACTION EXTRACTOR STARTED =====")

    prompt = f"""
Extract all action items from the email.

Return ONLY JSON.

Format:

{{
  "action_items": [
    {{
      "task": "",
      "deadline": "",
      "owner": ""
    }}
  ]
}}

Email:

{email_content}
"""

    response = model.invoke(prompt)

    print("Raw Action Extraction Response:")
    print(response)

    response = str(response)

    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()

    result = json.loads(response)

    print("Parsed Action Items:")
    print(result)

    return result

@tool
def schedule_meeting(email_content: str) -> dict:
    """
    Extract meeting details from an email.
    """

    print("\n===== MEETING DETECTOR STARTED =====")

    prompt = f"""
Analyze the email.

If a meeting is requested extract:

- date
- time
- attendees
- email of participants

Return ONLY JSON.

{{
    "meeting_detected": true,
    "meeting_date": "",
    "meeting_time": "",
    "attendees": [],
    "emails": []
}}

Email:

{email_content}
"""

    response = model.invoke(prompt)

    print("Raw Scheduler Response:")
    print(response)
    response = str(response)

    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()

    result = json.loads(response)

    print("Parsed Meeting Data:")
    print(result)

    return result

@tool
def memory_lookup(query: str) -> dict:
    """
    Simulated memory lookup.
    """

    print("\n===== MEMORY LOOKUP =====")
    print("Query:", query)

    memory = {
        "preferred_tone": "professional",
        "meeting_preference": "afternoon",
        "manager": "Ravi"
    }

    print("Memory Found:")
    print(memory)

    return memory

@tool
def response_drafter_tool(email_content: str) -> dict:
    """
    Create a professional email response.
    """

    print("\n===== RESPONSE DRAFTER STARTED =====")

    prompt = f"""
Draft a professional response.

The response should:

1. Acknowledge the sender.
2. Confirm action items if present.
3. Confirm meeting attendance if applicable.
4. Maintain a professional tone.

Email:

{email_content}

Return ONLY JSON.

{{
    "draft_response": ""
}}
"""

    response = model.invoke(prompt)

    print("Raw Draft Response:")
    print(response)
    response = str(response)
    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()

    result = json.loads(response)

    print("Draft Generated:")
    print(result)

    return result




#     prompt = f"""
# Today's date is {today}.

# Extract meeting information.

# Normalize:

# - Date => YYYY-MM-DD
# - Time => HH:MM (24 hour)

# Return ONLY JSON.

# {{
#     "meeting_date": "",
#     "meeting_time": "",
#     "duration_minutes": 30,
#     "attendees": [],
#     "missing_information": []
# }}

# Email:

# {email_content}
# """