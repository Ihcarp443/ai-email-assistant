from langchain_core.messages import AIMessage, ToolMessage
from services.utils import unwrap   
from graph.state import EmailState


def create_agent_node(email_agent):

    async def agent_node(state: EmailState):
        # print("entered agent")

        result = await email_agent.ainvoke(
            {"messages": [{"role": "user", "content": f"""
Process this email.

Subject:
{state["subject"]}

Sender:
{state["sender"]}

Body:
{state["body"]}

Category:
{state["category"]}
"""}]}
        )
        

        called, availability = [], {}
        for m in result["messages"]:
            if isinstance(m, AIMessage):
                for c in m.tool_calls:
                    called.append(c["name"])
                    print(f"TOOL CALL   -> {c['name']} {c['args']}")
            elif isinstance(m, ToolMessage):
                print(f"TOOL RESULT <- {m.name}: {str(m.content)[:300]}")
                if m.name == "check_calendar_availability":
                    availability = unwrap(m.content)

        if "extract_meeting_details" in called and "check_calendar_availability" not in called:
            print("WARNING: meeting detected but availability was never checked")

        return {
            "messages": result["messages"],
            "availability": availability,         
            "tool_outputs": {"agent_result": result},
            "status": "AGENT_COMPLETED",
        }
    return agent_node