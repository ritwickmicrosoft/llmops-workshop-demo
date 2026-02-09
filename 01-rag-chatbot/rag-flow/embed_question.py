"""
Embed Question Node - Generate embedding for user question
Uses Azure OpenAI text-embedding-3-large model with RBAC authentication
"""

from promptflow.core import tool
from promptflow.connections import AzureOpenAIConnection
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential


@tool
def embed_question(question: str, connection: AzureOpenAIConnection) -> list:
    """
    Generate an embedding vector for the user's question.
    
    Args:
        question: The user's input question
        connection: Azure OpenAI connection (uses Managed Identity)
    
    Returns:
        List of floats representing the embedding vector
    """
    # Use DefaultAzureCredential for RBAC authentication
    credential = DefaultAzureCredential()
    
    client = AzureOpenAI(
        azure_endpoint=connection.api_base,
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-02-01"
    )
    
    response = client.embeddings.create(
        input=question,
        model="text-embedding-3-large"
    )
    
    return response.data[0].embedding
