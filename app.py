# app.py

import streamlit as st
from typing import List
import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from agents.chat_agent import create_agent, get_chat_config
import json
from agents.utils.visualization import visualize_neo4j_results_v1,visualize_neo4j_results_v2 
import streamlit.components.v1 as components
import getpass
from langchain_community.chat_message_histories import SQLChatMessageHistory

# Load environment variables
load_dotenv(override=True)

def initialize_page():
    st.set_page_config(
        page_title="AML/OFAC GraphRAG Chatbot",
        page_icon="🤖",
        layout="wide"
    )

def process_message(prompt: str, chat_container):
    """Process a message and update the chat"""
    if not prompt.strip():
        return
    
    user_message = HumanMessage(content=prompt)

    with chat_container.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append(user_message)

    with chat_container.chat_message("assistant"):
        with st.spinner("Processing query..."):
            try:
                # Get response from agent
                result = st.session_state.agent_workflow.invoke(
                    {"messages": st.session_state.messages.copy()},
                     config=st.session_state.chat_config
                )

                # First display the final AI response
                last_message = result["messages"][-1]
                if isinstance(last_message, AIMessage):
                    st.markdown(last_message.content)
                    st.session_state.messages.append(last_message)
                
                # Then process tool message if exists
                for msg in result["messages"]:
                    if isinstance(msg, ToolMessage) and msg.name == "cypher_qa":
                        try:
                            tool_content = json.loads(msg.content)

                            # Debug
                            # print(f"tool_content: {tool_content}")

                            if "intermediate_steps" in tool_content:
                                # Get the actual executed query
                                cypher_query = tool_content["intermediate_steps"][0]["query"].replace("cypher\n", "")
                                with st.expander("View Cypher Query"):
                                    st.code(cypher_query, language="cypher")

                                # Process visualization if context exists
                                if len(tool_content["intermediate_steps"]) > 1:

                                    # print(f"\nsteps: {len(tool_content["intermediate_steps"])}")

                                    cypher_result = tool_content["intermediate_steps"][1].get("context")
                                    if cypher_result:
                                        visualization_html = visualize_neo4j_results_v2(
                                            {"cypher_result": cypher_result, "generated_cypher": cypher_query}
                                        )
                                        if visualization_html:
                                            st.markdown("### Graph Visualization")
                                            # Fixed the components.html reference
                                            st.components.v1.html(
                                                visualization_html, 
                                                height=650, 
                                                width=650,
                                                scrolling=True
                                            )
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse tool message: {e}")
                            st.error("Failed to parse tool message")

                

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                print(f"Full error: {e}")

def main():
    # Initialize username in session state if not present
    if "username" not in st.session_state:
        try:
            st.session_state.username = getpass.getuser()
        except Exception as e:
            st.warning("Could not get system username. Using default.")
            st.session_state.username = "default_user"

    # Initialize agent workflow and chat configuration with username
    if "agent_workflow" not in st.session_state:
        st.session_state.agent_workflow = create_agent()
        st.session_state.chat_config = get_chat_config()

    # Initialize messages for display
    if "messages" not in st.session_state:
        st.session_state.messages = [
            AIMessage(content="Hello, how can I help you today?")
        ]
    
    if "selected_question" not in st.session_state:
        st.session_state.selected_question = None

    initialize_page()

    # Main title
    st.title("🤖AML/OFAC GraphRAG Chatbot")

    # About Me expander
    with st.expander("About Me"):

        

        st.markdown("""
        ### Overview
        This is a ReAct Chatbot developed using the LangGraph framework, designed to provide intelligent querying capabilities over OFAC (Office of Foreign Assets Control) sanctions data.

        """)

                # Image display with size control
        st.image("schema.PNG", 
                caption="Graph Schema", 
                width=300) 


        st.markdown("""

        ### Tools
        The chatbot is equipped with two primary tools:
        * **GraphCypherQAChain**: Enables natural language querying of the Neo4j graph database
        * **TavilySearchResults**: Provides real-time web search capabilities for supplementary information

        The graph database is populated with data from the [OFAC](https://sanctionssearch.ofac.treas.gov), providing comprehensive information about sanctioned entities.


        ### Technical Details
        * **Reasoning LLM**: GPT-4o
        * **Framework**: LangGraph
                    
        ### Graph Workflow
                    """)
        
        st.image("chat_graph.PNG", 
                caption="LangGraph Workflow", 
                width=300) 

        st.markdown("""

        ### Required Environment Variables
        * `OPENAI_API_KEY`: OpenAI API authentication
        * `TAVILY_API_KEY`: Tavily search API authentication

        ### Optional LangSmith Tracing
        * `LANGCHAIN_API_KEY`: LangChain API key
        * `LANGCHAIN_TRACING_V2`: Enable LangSmith tracing
        * `LANGCHAIN_ENDPOINT`: LangSmith endpoint
        * `LANGSMITH_PROJECT`: Project name for tracking

        ### More Information
        - Obtain OpenAI AAPI key from [OpenAI](https://platform.openai.com/)
        - Obtain Tavily API key from [Tavily](https://tavily.com/)
        - For detailed insights and tracking, visit [LangSmith](https://www.langchain.com/langsmith)
        - For detailed LangGraph implementation, visit [LangGraph](https://langchain-ai.github.io/langgraph/)
        """)

    # Sidebar
    with st.sidebar:
        st.header("Options")
        if st.button("Clear Conversation", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_config = get_chat_config()  # Generate new config
            st.rerun()
        
        st.header("Quick Questions")
        questions = [
            "What is money laudering and what is the impact?",
            "What is the latest news about US sanctions?",
            "Find all information about one person that goes by name Ayman",
            "Find persons who has alias more than 10",
            "Do we have information about one person that goes by name Alcides , and can you search internet for the latest news or article about him",
            "List out all program name",
            "Find people sanctioned in 'SDGT' programs",
            "Can you search the web for latest news Jihad Group",
            "How to cook chicken?",
            "MATCH (n) DELETE n"
        ]
        
        for question in questions:
            if st.button(question, use_container_width=True):
                st.session_state.selected_question = question
                st.rerun()

    # Chat container for history
    chat_container = st.container()

    # Display existing chat history
    with chat_container:
        for message in st.session_state.messages:
            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.markdown(message.content)
            elif isinstance(message, AIMessage):
                with st.chat_message("assistant"):
                    st.markdown(message.content)
                    
                    # If there's a stored cypher query for this message
                    if hasattr(message, 'cypher_query'):
                        with st.expander("View Cypher Query"):
                            st.code(message.cypher_query, language="cypher")
                            
            elif isinstance(message, ToolMessage):
                with st.chat_message("assistant"):
                    st.markdown(f"🔧 Tool ({message.name}): {message.content}")

    # Handle quick question selection
    if st.session_state.selected_question:
        process_message(st.session_state.selected_question, chat_container)
        st.session_state.selected_question = None
    
    # Chat input at the bottom
    prompt_placeholder = "Click to select quick question from the left, or enter your query..."
    if prompt := st.chat_input(prompt_placeholder):
        process_message(prompt, chat_container)

if __name__ == "__main__":
    main()