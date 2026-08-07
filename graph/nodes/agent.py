from graph.state import EmailState
from agents.email_agent import email_agent


def agent_node(state: EmailState):

    print("entered agent")

    result = email_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Process this email.

Subject:
{state["subject"]}

Sender:
{state["sender"]}

Body:
{state["body"]}
"""
                }
            ]
        }
    )

    print("\n===== AGENT RESULT =====")
    print(result)

    return {
        "messages": result["messages"],
        "tool_outputs": {
            "agent_result": result
        },
        "status": "AGENT_COMPLETED"
    }