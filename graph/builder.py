from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import EmailState
from graph.nodes.classifier import classification_node
from graph.nodes.agent import create_agent_node
from graph.nodes.fetch_node import fetch_email_node
from agents.email_agent import create_email_agent


def create_graph(calendar_tool):

    email_agent = create_email_agent(calendar_tool)

    builder = StateGraph(EmailState)

    builder.add_node("fetch", fetch_email_node)
    builder.add_node("classifier", classification_node)
    builder.add_node("agent", create_agent_node(email_agent))

    builder.add_edge(START, "fetch")
    builder.add_edge("fetch", "classifier")
    builder.add_edge("classifier", "agent")
    builder.add_edge("agent", END)

    checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)