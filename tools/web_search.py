# tools/web_search.py

from typing import Any
from langchain.tools import BaseTool
from langchain_community.tools.tavily_search import TavilySearchResults

class TavilySearchTool(BaseTool):
    """Tool for performing web searches using Tavily"""
    name: str = "web_search"
    description: str = """Use this tool to search for supplementary information about:
        - Sanctions programs and regulations
        - Updates to sanctions lists
        - AML compliance requirements
        - Financial crime prevention
        - International regulatory frameworks
        Do NOT use this tool for general web searches or unrelated topics."""
    
    def _run(self, query: str) -> str:
        """Run the tool."""
        try:
            search = TavilySearchResults(
                max_results=3,
                search_depth='advanced',
                include_answer=True,
                include_raw_content=True,
            )
            
            response = search.invoke(query)
            return str(response)
        except Exception as e:
            return f"Error performing web search: {str(e)}"
            
    def _arun(self, query: str) -> str:
        """TODO: Implement async version if needed"""
        raise NotImplementedError("Async version not implemented")