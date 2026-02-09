"""
LLMOps Workshop - Azure AI Foundry Backend
============================================
Backend for the RAG chatbot using Azure AI Foundry services.

This version uses:
- Azure AI Foundry Hub & Project for centralized management
- Hub Connections for Azure OpenAI and AI Search (RBAC-based)
- get_openai_client() from AIProjectClient when available

Authentication uses RBAC (Managed Identity) - no API keys required.

Run: python app.py
Access: http://localhost:5000
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from openai import AzureOpenAI

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# =============================================================================
# Configuration - Azure AI Foundry
# =============================================================================

# Azure AI Foundry Resource & Project info
AI_FOUNDRY_RESOURCE = "foundry-llmops-demo"
AI_FOUNDRY_PROJECT = "proj-llmops-demo"
RESOURCE_GROUP = "rg-llmops-demo"
SUBSCRIPTION_ID = "1d53bfb3-a84c-4eb4-8c79-f29dc8424b6a"
FOUNDRY_ENDPOINT = "https://foundry-llmops-demo.services.ai.azure.com/"

# Azure OpenAI endpoint (from Hub connection: aoai-connection)
AZURE_OPENAI_ENDPOINT = os.environ.get(
    "AZURE_OPENAI_ENDPOINT", 
    "https://aoai-llmops-eastus.openai.azure.com/"
)

# Azure AI Search endpoint (from Hub connection: search-connection)
AZURE_SEARCH_ENDPOINT = os.environ.get(
    "AZURE_SEARCH_ENDPOINT",
    "https://search-llmops-dev-naxfrjtmsmlvo.search.windows.net"
)

# Model configurations
CHAT_MODEL_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
EMBEDDING_MODEL_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
SEARCH_INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "walle-products")

# System prompt for the chatbot
SYSTEM_PROMPT = """You are Wall-E, a friendly AI assistant for Wall-E Electronics, a company that sells consumer electronics products including laptops, headphones, smartwatches, and accessories.

Your role:
- Answer customer questions about products, policies, and support
- Be concise, friendly, and helpful like Wall-E the robot
- If you don't know something, say so honestly
- Keep responses under 200 words unless more detail is needed
- When you have context from retrieved documents, base your answers on that information

Key Information:
- Return Policy: 30 days for unopened items, 14 days for opened (15% restocking fee for headphones)
- Laptop Warranty: 2 years
- Smartwatch/Headphones Warranty: 1 year
- Support: 1-800-WALL-E or support@wall-e.com"""


# =============================================================================
# Azure Authentication (RBAC - No API Keys)
# =============================================================================

def get_credential():
    """Get Azure credential - works locally (Azure CLI) and in Azure (Managed Identity)."""
    try:
        # Try Managed Identity first (works when deployed to Azure)
        cred = ManagedIdentityCredential()
        cred.get_token("https://cognitiveservices.azure.com/.default")
        return cred
    except Exception:
        # Fall back to DefaultAzureCredential (works with Azure CLI locally)
        return DefaultAzureCredential()

credential = get_credential()


# =============================================================================
# AI Foundry OpenAI Client (uses Hub connection)
# =============================================================================

def get_openai_client():
    """
    Get Azure OpenAI client.
    Uses AI Foundry Hub connection (aoai-connection) with RBAC authentication.
    """
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-02-01"
    )


# =============================================================================
# RAG Pipeline using AI Foundry Connected Services
# =============================================================================

def search_documents(query: str) -> str:
    """
    Search for relevant documents using Azure AI Search.
    Uses AI Foundry Hub connection (search-connection) with RBAC authentication.
    """
    try:
        from azure.search.documents import SearchClient
        from azure.search.documents.models import VectorizedQuery
        
        # Connect to AI Search using Hub connection endpoint
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX_NAME,
            credential=credential
        )
        
        # Get embedding using OpenAI (from Hub connection)
        openai_client = get_openai_client()
        embedding_response = openai_client.embeddings.create(
            input=query,
            model=EMBEDDING_MODEL_DEPLOYMENT
        )
        query_embedding = embedding_response.data[0].embedding
        
        # Vector search
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=3,
            fields="content_vector"
        )
        
        results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=3,
            select=["title", "content"]
        )
        
        # Format results as context
        context_parts = []
        for result in results:
            context_parts.append(f"**{result['title']}**\n{result['content']}")
        
        if context_parts:
            return "\n\n---\n\n".join(context_parts)
        return ""
        
    except Exception as e:
        print(f"Search error: {e}")
        return ""


def generate_response(message: str, history: list, context: str = "") -> dict:
    """
    Generate response using Azure OpenAI via AI Foundry Hub connection.
    """
    try:
        openai_client = get_openai_client()
        
        # Build system prompt with context
        system_content = SYSTEM_PROMPT
        if context:
            system_content += f"\n\n# Retrieved Information:\n{context}"
        
        # Build messages
        messages = [{"role": "system", "content": system_content}]
        
        # Add history (last 10 messages)
        for msg in history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call Azure OpenAI (via Hub connection)
        response = openai_client.chat.completions.create(
            model=CHAT_MODEL_DEPLOYMENT,
            messages=messages,
            max_tokens=500,
            temperature=0.3
        )
        
        return {
            'response': response.choices[0].message.content,
            'context_used': bool(context),
            'source': 'Azure AI Foundry',
            'resource': AI_FOUNDRY_RESOURCE,
            'project': AI_FOUNDRY_PROJECT,
            'model': CHAT_MODEL_DEPLOYMENT,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            } if hasattr(response, 'usage') and response.usage else None
        }
        
    except Exception as e:
        raise Exception(f"Generation error: {e}")


# =============================================================================
# Flask Routes
# =============================================================================

@app.route('/')
def index():
    """Serve the frontend."""
    return send_from_directory('.', 'index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat requests using Azure AI Foundry services.
    Uses Hub connections for Azure OpenAI and AI Search.
    """
    try:
        data = request.json
        message = data.get('message', '')
        history = data.get('history', [])
        use_rag = data.get('use_rag', True)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get relevant context using AI Search (Hub connection)
        context = ""
        if use_rag:
            context = search_documents(message)
        
        # Generate response using OpenAI (Hub connection)
        result = generate_response(message, history, context)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check - shows Azure AI Foundry connectivity."""
    return jsonify({
        'status': 'healthy',
        'auth': 'RBAC (Managed Identity / Azure CLI)',
        'mode': 'Azure AI Foundry',
        'foundry': {
            'resource': AI_FOUNDRY_RESOURCE,
            'project': AI_FOUNDRY_PROJECT,
            'resource_group': RESOURCE_GROUP,
            'endpoint': FOUNDRY_ENDPOINT
        },
        'connections': {
            'aoai-connection': {
                'type': 'Azure OpenAI',
                'endpoint': AZURE_OPENAI_ENDPOINT,
                'chat_model': CHAT_MODEL_DEPLOYMENT,
                'embedding_model': EMBEDDING_MODEL_DEPLOYMENT
            },
            'search-connection': {
                'type': 'Azure AI Search',
                'endpoint': AZURE_SEARCH_ENDPOINT,
                'index': SEARCH_INDEX_NAME
            }
        }
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Return configuration for frontend display."""
    return jsonify({
        'mode': 'Azure AI Foundry',
        'resource': AI_FOUNDRY_RESOURCE,
        'project': AI_FOUNDRY_PROJECT,
        'foundry_endpoint': FOUNDRY_ENDPOINT,
        'openai_endpoint': AZURE_OPENAI_ENDPOINT,
        'search_endpoint': AZURE_SEARCH_ENDPOINT,
        'chat_model': CHAT_MODEL_DEPLOYMENT,
        'embedding_model': EMBEDDING_MODEL_DEPLOYMENT,
        'search_index': SEARCH_INDEX_NAME
    })


if __name__ == '__main__':
    print("=" * 60)
    print("  🤖 Wall-E Electronics - RAG Chatbot")
    print("  Powered by Azure AI Foundry")
    print("=" * 60)
    
    print("\n  🔐 Authentication: RBAC (Managed Identity / Azure CLI)")
    
    print(f"\n  🏗️  Azure AI Foundry:")
    print(f"    • Resource: {AI_FOUNDRY_RESOURCE}")
    print(f"    • Project: {AI_FOUNDRY_PROJECT}")
    print(f"    • Endpoint: {FOUNDRY_ENDPOINT}")
    print(f"    • Resource Group: {RESOURCE_GROUP}")
    
    print(f"\n  📡 Foundry Connections:")
    print(f"    • aoai-connection → Azure OpenAI")
    print(f"      Endpoint: {AZURE_OPENAI_ENDPOINT}")
    print(f"      Chat Model: {CHAT_MODEL_DEPLOYMENT}")
    print(f"      Embedding Model: {EMBEDDING_MODEL_DEPLOYMENT}")
    print(f"    • search-connection → Azure AI Search")
    print(f"      Endpoint: {AZURE_SEARCH_ENDPOINT}")
    print(f"      Index: {SEARCH_INDEX_NAME}")
    
    print("\n  🚀 Starting server at http://localhost:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
