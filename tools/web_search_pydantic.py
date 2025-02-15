# tools/web_search.py

from typing import List, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
import os
import json

class SearchResult(BaseModel):
    """Structure for web search results"""
    title: str = Field(description="Title of the search result")
    url: str = Field(description="URL of the search result")
    content: str = Field(description="Summary or content of the search result")
    relevance_score: Optional[float] = Field(
        description="Relevance score from 0 to 1", 
        default=None
    )

class WebSearchResults(BaseModel):
    """Container for multiple search results"""
    query: str = Field(description="The original search query")
    results: List[SearchResult] = Field(description="List of search results")
    total_results: int = Field(description="Total number of results found")

# Create parser
search_parser = PydanticOutputParser(pydantic_object=WebSearchResults)

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
            
            raw_response = search.invoke(query)
            
            # Format results into our Pydantic model
            search_results = [
                SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    relevance_score=result.get("score")
                )
                for result in raw_response if isinstance(result, dict)
            ]
            
            # Create full results object
            formatted_results = WebSearchResults(
                query=query,
                results=search_results,
                total_results=len(search_results)
            )
            
            return formatted_results.model_dump()
            
        except Exception as e:
            # Return error in a structured way
            return WebSearchResults(
                query=query,
                results=[],
                total_results=0
            ).model_dump()
            
    def _arun(self, query: str) -> str:
        """TODO: Implement async version if needed"""
        raise NotImplementedError("Async version not implemented")
    

def pretty_print_results(results):
    """Helper function to print results in a readable format"""
    print("\nSearch Query:", results.get('query'))
    print("Total Results:", results.get('total_results'))
    print("\nResults:")
    for i, result in enumerate(results.get('results', []), 1):
        print(f"\n--- Result {i} ---")
        print("Title:", result.get('title'))
        print("URL:", result.get('url'))
        print("Content:", result.get('content'))
        if result.get('relevance_score'):
            print("Relevance Score:", result.get('relevance_score'))
    if 'error' in results:
        print("\nError:", results['error'])

if __name__ == "__main__":
    # Load environment variables
    load_dotenv('../.env',override=True)
    
    # Check for API key
    if not os.getenv("TAVILY_API_KEY"):
        print("Error: TAVILY_API_KEY not found in environment variables")
        print("Please set your Tavily API key in the .env file or environment variables")
        exit(1)
        
    # Create search tool and run test query
    try:
        search_tool = TavilySearchTool()
        print("Running search...")
        results = search_tool.run("latest updates on US sanctions programs")
        
        # Print results in a readable format
        pretty_print_results(results)
        
        # Also save to file for reference
        with open('search_results.json', 'w') as f:
            json.dump(results, f, indent=2)
            print("\nResults also saved to search_results.json")
            
    except Exception as e:
        print(f"Error running search: {e}")