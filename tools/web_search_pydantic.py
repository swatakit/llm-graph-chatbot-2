# tools/web_search_pydantic.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from tavily import TavilyClient
import os
from dotenv import load_dotenv
import json

class SearchResult(BaseModel):
    """Structure for web search results"""
    title: str = Field(description="Title of the search result")
    url: str = Field(description="URL of the search result")
    content: str = Field(description="Summary or content of the search result")
    score: float = Field(description="Relevance score from 0 to 1")
    raw_content: Optional[str] = Field(description="Raw content if available")

class WebSearchResults(BaseModel):
    """Container for multiple search results"""
    query: str = Field(description="The original search query")
    results: List[SearchResult] = Field(description="List of search results")
    total_results: int = Field(description="Total number of results found")
    response_time: Optional[float] = Field(description="Response time in seconds")
    follow_up_questions: Optional[List[str]] = Field(description="Follow up questions if any")
    answer: Optional[str] = Field(description="Direct answer if available")
    images: List[str] = Field(default_factory=list, description="List of image URLs")

class TavilySearchTool(BaseTool):
    """Tool for performing web searches specific to sanctions and AML information"""
    name: str = "web_search"
    description: str = """Use this tool to search for supplementary information about:
        - Sanctions programs and regulations
        - Updates to sanctions lists
        - AML compliance requirements
        - Financial crime prevention
        - International regulatory frameworks
        Do NOT use this tool for general web searches or unrelated topics."""
    
    def _run(self, query: str) -> Dict[str, Any]:
        """Run the tool."""
        try:
            # Initialize Tavily client
            client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
            
            # Get response from Tavily
            response = client.search(
                query=query,
                search_depth="advanced",
                include_answer="advanced",
                include_raw_content=True,
                include_images=True,
                max_results=3
            )
            
            # Create Pydantic model instance
            formatted_results = WebSearchResults(
                query=response.get("query", query),
                results=response.get("results", []),
                total_results=len(response.get("results", [])),
                response_time=response.get("response_time"),
                follow_up_questions=response.get("follow_up_questions"),
                answer=response.get("answer"),
                images=response.get("images", [])
            )
            
            return formatted_results.model_dump()
            
        except Exception as e:
            error_results = WebSearchResults(
                query=query,
                results=[],
                total_results=0,
                images=[]
            ).model_dump()
            error_results['error'] = str(e)
            return error_results

def print_results_json(results: Dict[str, Any], indent: int = 2, file_path: str = None):
    """
    Print search results in JSON format with optional file output.
    
    Args:
        results: Dictionary containing search results
        indent: Number of spaces for JSON indentation (default: 2)
        file_path: Optional path to save JSON output to a file
    """
    # Convert to JSON string with proper formatting
    json_output = json.dumps(results, indent=indent, ensure_ascii=False)
    
    # Print to console
    print(json_output)
    
    # If file path is provided, save to file
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_output)

def pretty_print_results(results):
    """Helper function to print results in a readable format"""
    print("\nSearch Query:", results.get('query'))
    print(f"Total Results: {results.get('total_results')}")
    
    if results.get('response_time'):
        print(f"Response Time: {results.get('response_time'):.2f}s")
    
    if results.get('answer'):
        print("\nDirect Answer:", results.get('answer'))
    
    print("\nResults:")
    for i, result in enumerate(results.get('results', []), 1):
        print(f"\n--- Result {i} ---")
        print(f"Title: {result.get('title')}")
        print(f"URL: {result.get('url')}")
        print(f"Content: {result.get('content')}")
        print(f"Score: {result.get('score'):.4f}")
    
    if results.get('follow_up_questions'):
        print("\nFollow-up Questions:")
        for q in results.get('follow_up_questions'):
            print(f"- {q}")
    
    if 'error' in results:
        print("\nError:", results['error'])

if __name__ == "__main__":
    # Load environment variables
    load_dotenv("../.env",override=True)

    
    if not os.getenv("TAVILY_API_KEY"):
        print("Error: TAVILY_API_KEY not found in environment variables")
        exit(1)
        
    try:
        search_tool = TavilySearchTool()
        print("Running search...")
        results = search_tool.run("latest updates on US sanctions programs")
        
        # Print results
        print_results_json(results, file_path="search_results.json")
        pretty_print_results(results)
        
    except Exception as e:
        print(f"Error running search: {e}")