# tools/web_search.py

from typing import Any
from langchain.tools import BaseTool
from langchain_community.tools.tavily_search import TavilySearchResults

class TavilySearchTool(BaseTool):
    """Tool for performing web searches using Tavily"""
    name: str = "web_search"
    description: str = "Search the web for realtime and latest information about news, stock market, weather updates etc."
    
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