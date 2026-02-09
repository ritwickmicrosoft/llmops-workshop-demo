"""
Retrieve Documents Node - Search AI Search index for relevant documents
Uses hybrid search (vector + keyword) with semantic ranking
"""

from promptflow.core import tool
from promptflow.connections import CognitiveSearchConnection
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.identity import DefaultAzureCredential


INDEX_NAME = "contoso-products"
TOP_K = 3  # Number of documents to retrieve


@tool
def retrieve_documents(
    question: str,
    question_embedding: list,
    connection: CognitiveSearchConnection
) -> str:
    """
    Retrieve relevant documents from Azure AI Search using hybrid search.
    
    Args:
        question: The user's input question (for keyword search)
        question_embedding: Vector embedding of the question
        connection: Azure AI Search connection (uses Managed Identity)
    
    Returns:
        Formatted string containing relevant document excerpts
    """
    # Use DefaultAzureCredential for RBAC authentication
    credential = DefaultAzureCredential()
    
    search_client = SearchClient(
        endpoint=connection.api_base,
        index_name=INDEX_NAME,
        credential=credential
    )
    
    # Create vector query
    vector_query = VectorizedQuery(
        vector=question_embedding,
        k_nearest_neighbors=TOP_K,
        fields="content_vector"
    )
    
    # Perform hybrid search (vector + keyword + semantic)
    results = search_client.search(
        search_text=question,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="semantic-config",
        top=TOP_K,
        select=["title", "category", "content", "last_updated"]
    )
    
    # Format results as context
    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(f"""
---
Source {i}: {result['title']}
Category: {result['category']}
Last Updated: {result['last_updated']}

{result['content']}
---
""")
    
    if not context_parts:
        return "No relevant documents found."
    
    return "\n".join(context_parts)
