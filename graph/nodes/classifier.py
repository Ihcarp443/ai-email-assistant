from langchain_core.messages import HumanMessage
from graph.state import EmailState
from services.llm import model
import json


EMAIL_CATEGORIES = [
    "Meeting Request",
    "Task / Action Required",
    "Support Request",
    "Information Request",
    "Approval Required",
    "Internal Communication",
    "Customer Query",
    "Follow Up",
    "Newsletter",
    "System Notification",
    "Spam",
    "General"
]

EMAIL_PRIORITIES = [
    "Critical",
    "High",
    "Medium",
    "Low"
]


def classification_node(state: EmailState):
    print("classification started")

    prompt = f"""
You are an email classification engine.

Choose ONLY from the provided values.

Valid Categories:
{EMAIL_CATEGORIES}

Valid Priorities:
{EMAIL_PRIORITIES}

Return ONLY valid JSON.

Email Subject:
{state["subject"]}

Email Body:
{state["body"]}

Output:

{{
    "category": "",
    "priority": ""
}}
"""
    try:
        response = model.invoke(prompt)
        print("response from llm classification", response)

    except Exception as e:
        print(e)
    
    if not isinstance(response, str):    
        response = str(response)

    response = response.strip()

    if response.startswith("```json"):
        response = response.replace("```json", "", 1)

    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()
    try:
        print("loading",response)
        js = json.loads(response)
        print(js)

    except Exception as e:
        print(e)


    result = json.loads(response)

    print("classification done", response)

    category = result["category"]
    priority = result["priority"]

    if category not in EMAIL_CATEGORIES:
        category = "General"

    if priority not in EMAIL_PRIORITIES:
        priority = "Medium"

    return {
        "category": category,
        "priority": priority,
        "status": "CLASSIFIED"
    }