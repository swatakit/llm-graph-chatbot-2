# agents/chat_agent.py

from typing import Dict, Any, List, Literal
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import START,END, StateGraph, MessagesState
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
import uuid
import getpass
import socket
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_community.chat_message_histories import SQLChatMessageHistory


# Initialize persistence memory saver 
conn = sqlite3.connect("checkpoints.sqlite",check_same_thread=False)
memory = SqliteSaver(conn)

def get_chat_config(username: str = None):
    """
    Generate configuration for chat session
    Args:
        username (str, optional): Username for the thread. If None, gets system username
    """
    if username is None:
        try:
            username = getpass.getuser()
        except Exception as e:
            print(f"Could not get system username: {e}")
            username = "default_user"
    
    hostname = socket.gethostname()
    print(f"thread_id: {username}_{hostname}")
    return {
        "configurable": {
            "thread_id": f"{username}_{hostname}",  # Combines username and hostname
            "checkpoint_ns": "graph_state",
            "checkpoint_id": str(uuid.uuid4())
        }
    }

def create_agent():
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o", # Note: the prompt works best with gpt-4
        temperature=0,
        streaming=True
    )
    
    # Import tools here to avoid circular imports
    # from tools.web_search import TavilySearchTool
    from tools.web_search_pydantic import TavilySearchTool
    from tools.cypher_qa import CypherQATool
    
    # Initialize tools
    tools = [
        TavilySearchTool(),
        CypherQATool(llm=llm)
    ]
    
    # Create ToolNode
    tool_node = ToolNode(tools)
    
    # Bind tools to the model
    model_with_tools = llm.bind_tools(tools)

    def should_continue(state: MessagesState):
        """Determine if we should continue the conversation or use tools"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    
    def call_model(state: MessagesState, config):
        """Call the model to get the next response"""

        # Initialize chat history
        chat_history = SQLChatMessageHistory(
            session_id=config["configurable"]["thread_id"],
            connection="sqlite:///chat_history.db"
        )

        messages = state["messages"]
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            system_message = SystemMessage(content="""
            You are a specialized assistant focused on researching about anti-money laundering, terrorist group, and querying a Neo4j database containing information about individuals, sanctions, aliases, and identity documents.

            Your capabilities:
            1. Use cypher_qa tool to query the Neo4j database for:
            - Information about persons
            - Sanctions and programs
            - Identity documents
            - Aliases and relationships

            2. Use web_search tool ONLY for supplementary information about sanctions and AML-related topics. Here is how you should process web search results:
            - Extract key points and recent developments
            - Organize information chronologically
            - Include relevant dates and sources
            - Summarize complex information clearly
            - Previde urls for further reading       
            - Include image if image links are provided.                    

            Database Safety Rules:
            - NEVER execute any commands that modify the database (DELETE, DROP, CREATE, SET, REMOVE, MERGE)
            - ONLY use READ operations (MATCH, WHERE, RETURN, WITH, UNWIND) 
            - If a user suggests a query with modification commands, explain that you can only perform read operations
            - Reject any queries containing ";" to prevent command chaining

            Important:
            - Only respond to queries related to the database content or AML/sanctions topics
            - For unrelated questions (like cooking, weather, general topics), politely explain that you are specialized in AML and sanctions data queries only
            - Always prioritize using the database over web search
            - If a query looks suspicious or could potentially harm the database, reject it and explain why

            Response Format:
            After answering each query:
            1. Analyze your response and the context of the user's question
            2. Generate 1-3 relevant follow-up questions that would:
            - Deepen the investigation
            - Explore related aspects of the current topic
            - Help clarify or expand on important details
            3. Format the follow-up questions as:
            "Related questions you might be interested in:
            - [Question 1]
            - [Question 2]
            - [Question 3]"
            """)

            messages.insert(0, system_message)
        
        # Get response from model
        response = model_with_tools.invoke(messages, config=config)

        # Save only new messages to chat history
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):  # Save only if last message was from human
            chat_history.add_message(last_message)
        chat_history.add_message(response)

        return {"messages": [response]}

  
    # Create the graph
    workflow = StateGraph(MessagesState)

    # Define the two nodes we will cycle between
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent", 
        should_continue, 
        ["tools", END]
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile the graph
    app = workflow.compile(checkpointer=memory)
    
    # Optional: Draw the graph
    # try:
    #     app.get_graph().draw_mermaid_png(output_file_path="chat_graph.png")
    # except Exception as e:
    #     print(f"Could not draw graph: {e}")
    
    return app