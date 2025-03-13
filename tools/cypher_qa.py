#tools/cypher_qa.py

from dataclasses import Field
from typing import Dict, Any, Optional, Type
from langchain.tools import BaseTool
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain.prompts.prompt import PromptTemplate
from langchain_core.tools import tool
import os

CYPHER_GENERATION_TEMPLATE = """
Task:Generate Cypher statement to query a graph database.
Instructions:
1. Use only the provided relationship types and properties in the schema.
2. Do not use any other relationship types or properties that are not provided.
3. **Always return the actual node objects (and the relationship if needed) so that the visualization code can draw edges.**
   - For example, return `RETURN p, a, r` instead of `RETURN a.fullname AS Alias`.
   - Even when only one node is queried, include the `MATCH` for relationships, i.e., `MATCH (n)-[r]-(p:Person)`, and ensure that the relationship (`r`) is part of the return, even if not explicitly required for the answer.
4. Do not include any embeddings in your output.

Schema:
{schema}

Question:
{question}

Cypher examples:

1. Find all information of one person by name
```
MATCH (n)-[r]-(p:Person) 
WHERE tolower(p.fullName) contains tolower("Ayman") 
RETURN n, r, p
```

2. Find people with multiple aliases more than 10
```
MATCH (p:Person)-[r:HAS_ALIAS]->(a:Alias)
WITH p, count(a) AS numAliases
WHERE numAliases > 10
MATCH (p)-[r:HAS_ALIAS]->(a:Alias)
RETURN p,r,a
```

3. List out all program name
```
MATCH (prog:Program) RETURN DISTINCT prog
```

4. Find people sanctioned by specific programs
```
MATCH (p:Person)-[s:SANCTIONED_BY]->(prog:Program)
WHERE prog.name IN ['SDGT', 'SYRIA']
RETURN p,s,prog
```


5. Find sanction programs with the count of persons in each
```
MATCH (p:Person)-[s:SANCTIONED_BY]->(prog:Program)
RETURN p,s,prog
```
"""

cypher_prompt = PromptTemplate.from_template(CYPHER_GENERATION_TEMPLATE)


CYPHER_QA_TEMPLATE = """Below are the results from a database query. Please provide a comprehensive response that:

1. Answers the question directly and clearly
2. Includes all relevant details from the results
3. Organizes information in a readable format using markdown when appropriate
4. Uses bullet points for multiple items
5. Adds relevant context about relationships between entities
6. Clarifies if any key information is missing

Query Results:
{context}

Question: {question}

Guidelines for response:
- Start with a clear, direct answer
- Use appropriate markdown formatting (bold for names, bullet points for lists)
- Explain relationships between entities when present
- For person queries, always include: full name, title, birth details if available
- For sanctions, mention programs and dates if available
- For documents, include document types and numbers
- If information is missing or incomplete, acknowledge this
- End with an invitation for follow-up questions if more details are needed

Response:"""


qa_prompt = PromptTemplate(input_variables=["context","question"], template=CYPHER_QA_TEMPLATE)


class CypherQATool(BaseTool):
    name: str = "cypher_qa"
    description: str = "Query a Neo4j graph database for information about individuals, sanctions, aliases, and identity documents"
    llm: Any 

    def __init__(self, llm: Any):
        """Initialize the tool with an LLM"""
        super().__init__(llm=llm)
    
    def _run(self, query: str) -> str:
        """Execute the tool."""
        try:
            chain = GraphCypherQAChain.from_llm(
                self.llm,
                graph=Neo4jGraph(
                    url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                    username=os.getenv("NEO4J_USER", "neo4j"),
                    password=os.getenv("NEO4J_PASSWORD", "password")
                ),
                verbose=True,
                return_intermediate_steps=True,
                cypher_prompt=cypher_prompt,
                qa_prompt=qa_prompt,
                allow_dangerous_requests = True
            )
            
            return chain.invoke(query)
        except Exception as e:
            return f"Error querying database: {str(e)}"
            
    def _arun(self, query: str) -> str:
        """TODO: Implement async version if needed"""
        raise NotImplementedError("Async version not implemented")
