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
    "meeting_related": True,
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
    result = json.loads(response)

    return result



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
    result = json.loads(response)

    return result

# ----------------------------------------------------
@tool
def extract_action_items(email_content: str) -> dict:
    """
    Extract action items from an email.
    """

    print("\n===== ACTION EXTRACTOR STARTED =====")

    prompt = f"""
You are an email action-item extraction system.

Your task is to extract ONLY genuine action items that are explicitly
required, assigned, committed to, or clearly stated as a task in the email.

IMPORTANT:
Do NOT convert every request, question, suggestion, or meeting discussion
into an action item.

An item is an ACTION ITEM only when the email clearly indicates that
someone needs to perform a task.

INCLUDE an action item when:

1. The sender explicitly assigns a task to the recipient or another person.
   Example:
   "Please send the report by Friday."
   -> action item: "Send the report"

2. The sender explicitly commits to doing something.
   Example:
   "I will send the report tomorrow."
   -> action item: "Send the report"

3. The email explicitly states that a task needs to be completed.
   Example:
   "We need to submit the application by Monday."
   -> action item: "Submit the application"

4. A task is explicitly requested using language such as:
   - please
   - send
   - update
   - complete
   - prepare
   - review
   - submit
   - confirm
   - provide
   - schedule
   - create
   - finalize
   - follow up

DO NOT include an action item when:

1. The sentence is only a question or suggestion.
2. The sender is asking about availability.
3. The sender is proposing or discussing a possible future action.
4. The email asks whether something is possible without explicitly assigning
   the task.
   Example:
   "Could we move the meeting to Monday?"
   -> NO action item
5. You would have to infer the task from context.
   NEVER invent an action item based on what would logically need to happen.

STRICT ANTI-HALLUCINATION RULE:
If there is no explicit action item in the email, return:
{{
  "action_items": []
}}

For each genuine action item:

- task: concise description of the explicitly stated task
- deadline: extract ONLY if explicitly stated; otherwise use ""
- owner: identify ONLY if explicitly stated or unambiguously assigned;
  otherwise use ""

NEVER invent an owner.
NEVER invent a deadline.
NEVER infer a task that is not explicitly stated.

Return ONLY valid JSON.

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
def response_drafter_tool(email_content: str, availability_note: str = "") -> dict:
    """Create a professional email response. For meeting emails, availability_note MUST
    summarize the check_calendar_availability result (free/busy, conflicts, alternatives)."""

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

Calendar availability: {availability_note or "NOT CHECKED"}
Rules: accept the meeting only if the note says free. If busy, decline politely and offer
the alternatives. If NOT CHECKED, do not confirm attendance.

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