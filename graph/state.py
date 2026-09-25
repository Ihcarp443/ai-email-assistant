from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import NotRequired
from typing import Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ActionItem(TypedDict):
    task: str
    deadline: Optional[str]
    owner: Optional[str]

class AgentAction(TypedDict):
    tool: str                          
    input: Dict[str, Any]
    reasoning: str
    status: str                     
    output: NotRequired[Dict[str, Any]]

class EmailState(TypedDict):
    email_id: str
    thread_id: str

    sender: str
    recipient: str

    subject: str
    body: str

    messages: Annotated[list[BaseMessage], add_messages]

    extracted_entities: Dict[str, Any]
    action_items: List[ActionItem]

    category: str
    priority: str

    retrieved_context: Dict[str, Any]

    reasoning: str
    agent_actions: List[AgentAction]

    tool_outputs: Dict[str, Any]

    availability: Dict[str, Any]
    status: str