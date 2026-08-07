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
    tool: str                          # draft_email, schedule_meeting, search_memory
    input: Dict[str, Any]
    reasoning: str
    status: str                        # pending | completed | failed
    output: NotRequired[Dict[str, Any]]

class EmailState(TypedDict):

    #  Email
    email_id: str
    thread_id: str

    sender: str
    recipient: str

    subject: str
    body: str

    #  Conversation Memory 
    messages: Annotated[list[BaseMessage], add_messages]

    #  Extractor Output 
    extracted_entities: Dict[str, Any]
    action_items: List[ActionItem]

    #  Classification 
    category: str
    priority: str
    intents: List[str]

    #  Long-Term Memory 
    retrieved_context: Dict[str, Any]

    #  Decision Agent 
    reasoning: str
    agent_actions: List[AgentAction]

    #  Tool Results 
    tool_outputs: Dict[str, Any]

    #  Graph Flow Status 
    status: str