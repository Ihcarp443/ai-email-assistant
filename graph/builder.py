from langgraph.graph import StateGraph
from langgraph.graph import START
from langgraph.graph import END
from langgraph.checkpoint.memory import MemorySaver 
from graph.state import EmailState
from graph.nodes.classifier import classification_node
from graph.nodes.agent import agent_node
from graph.nodes.fetch_node import fetch_email_node
# from langgraph.checkpoint.

builder = StateGraph(EmailState)

builder.add_node(
    "fetch",
    fetch_email_node
)

builder.add_node(
    "classifier",
    classification_node
)

builder.add_node(
    "agent",
    agent_node
)

builder.add_edge(
    START,
    "fetch"
)

builder.add_edge(
    "fetch",
    "classifier"
)

builder.add_edge(
    "classifier",
    "agent"
)

builder.add_edge(
    "agent",
    END
)

checkpointer = MemorySaver()

graph = builder.compile(
    checkpointer=checkpointer
)

print("graph compiled successfully!!")