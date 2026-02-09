"""
LLMOps Workshop - Create Azure AI Search Index with Sample Documents
=====================================================================
This script creates a vector search index in Azure AI Search and populates it
with sample product documentation for the Wall-E Electronics chatbot demo.

Authentication: Uses Azure Identity (DefaultAzureCredential) - no API keys required
"""

import os
import json
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)
from openai import AzureOpenAI

# Configuration from environment variables
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "https://search-llmops-dev-naxfrjtmsmlvo.search.windows.net")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://aoai-llmops-eastus.openai.azure.com/")
EMBEDDING_MODEL = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
INDEX_NAME = "contoso-products"

# Sample product documentation
SAMPLE_DOCUMENTS = [
    {
        "id": "policy-returns-001",
        "title": "Return Policy - Electronics",
        "category": "Policy",
        "content": """Wall-E Electronics Return Policy

All electronics purchases can be returned within 30 days of purchase for a full refund. 
The item must be in its original packaging and in unused condition.

For headphones and audio equipment:
- 30-day return window for unopened items
- 14-day return window for opened items (restocking fee of 15% applies)
- Items must include all original accessories and documentation

For laptops and computers:
- 30-day return window
- Must be factory reset before return
- All original accessories must be included

To initiate a return:
1. Log into your Wall-E account
2. Go to Order History
3. Select the item and click "Return"
4. Print the prepaid shipping label
5. Drop off at any authorized carrier location

Refunds are processed within 5-7 business days after we receive the item.""",
        "last_updated": "2025-01-15"
    },
    {
        "id": "product-smartwatch-x200",
        "title": "SmartWatch X200 User Guide",
        "category": "Product",
        "content": """SmartWatch X200 User Guide

Getting Started:
1. Charge the watch fully before first use (approximately 2 hours)
2. Press and hold the side button for 3 seconds to power on
3. Download the Wall-E Wear app from your phone's app store
4. Follow the pairing instructions in the app

How to Reset Your SmartWatch X200:
Method 1 - Soft Reset:
- Press and hold the side button for 10 seconds until the logo appears
- Release the button and wait for restart

Method 2 - Factory Reset:
- Go to Settings > System > Reset
- Select "Factory Reset"
- Confirm by entering your PIN
- The watch will restart with default settings

Troubleshooting:
- If the watch won't turn on, charge for at least 30 minutes
- If Bluetooth won't connect, restart both the watch and phone
- If the heart rate sensor is inaccurate, clean the sensor and tighten the band

Specifications:
- Battery life: Up to 7 days
- Water resistance: 5ATM
- Display: 1.4" AMOLED
- Sensors: Heart rate, SpO2, accelerometer, gyroscope""",
        "last_updated": "2025-02-01"
    },
    {
        "id": "policy-warranty-001",
        "title": "Warranty Policy",
        "category": "Policy",
        "content": """Wall-E Electronics Warranty Policy

Standard Warranty Coverage:
- Laptops and Computers: 2 years from date of purchase
- Smartphones and Tablets: 1 year from date of purchase
- Headphones and Audio: 1 year from date of purchase
- Smartwatches and Wearables: 1 year from date of purchase
- Accessories: 90 days from date of purchase

What's Covered:
- Manufacturing defects
- Hardware malfunctions under normal use
- Battery defects (capacity drops below 80% within warranty period)
- Display defects (dead pixels, burn-in)

What's NOT Covered:
- Physical damage (drops, cracks, water damage beyond rated resistance)
- Software issues or user modifications
- Normal wear and tear
- Damage from unauthorized repairs
- Lost or stolen items

Extended Warranty:
Wall-E Care+ extends your warranty to 3 years and includes:
- Accidental damage protection (2 incidents)
- Priority support
- Free battery replacement
- 20% discount on accessories

To file a warranty claim:
1. Contact Wall-E Support at support@wall-e.com
2. Provide your order number and product serial number
3. Describe the issue in detail
4. Our team will guide you through next steps""",
        "last_updated": "2025-01-20"
    },
    {
        "id": "product-laptop-pro15",
        "title": "Wall-E Laptop Pro 15 Specifications",
        "category": "Product",
        "content": """Wall-E Laptop Pro 15 - Complete Specifications

Display:
- 15.6" 4K OLED display (3840 x 2160)
- 100% DCI-P3 color gamut
- 500 nits peak brightness
- Anti-glare coating

Processor Options:
- Intel Core i7-13700H (base configuration)
- Intel Core i9-13900H (performance configuration)

Memory & Storage:
- RAM: 16GB / 32GB / 64GB DDR5
- Storage: 512GB / 1TB / 2TB NVMe SSD

Graphics:
- NVIDIA GeForce RTX 4060 (base)
- NVIDIA GeForce RTX 4070 (optional upgrade)

Battery:
- 86 Wh battery
- Up to 12 hours video playback
- 140W USB-C fast charging (0-50% in 30 minutes)

Connectivity:
- Wi-Fi 6E
- Bluetooth 5.3
- 2x Thunderbolt 4 ports
- 1x USB-A 3.2 port
- HDMI 2.1
- SD card reader

Dimensions & Weight:
- 355 x 235 x 16.9 mm
- 1.8 kg

Included in Box:
- Laptop Pro 15
- 140W USB-C Power Adapter
- USB-C cable
- Quick Start Guide
- Warranty card""",
        "last_updated": "2025-01-10"
    },
    {
        "id": "support-troubleshooting-001",
        "title": "Common Troubleshooting Steps",
        "category": "Support",
        "content": """Wall-E Electronics - Common Troubleshooting Guide

Laptop Issues:

"My laptop won't turn on"
1. Connect the charger and wait 10 minutes
2. Press and hold power button for 15 seconds
3. Release and press power button normally
4. If no response, try a different outlet/charger

"Laptop is running slow"
1. Restart the laptop
2. Check for Windows updates
3. Close unnecessary background applications
4. Run disk cleanup utility
5. Consider upgrading RAM or switching to SSD

"Battery draining quickly"
1. Reduce screen brightness
2. Disable Wi-Fi/Bluetooth when not in use
3. Check battery health in Settings > System > Power
4. Contact support if health is below 80%

Headphones Issues:

"Bluetooth won't connect"
1. Turn off headphones, wait 10 seconds, turn on
2. Remove device from Bluetooth settings and re-pair
3. Reset headphones by holding power button 20 seconds
4. Update firmware via Wall-E Audio app

"Audio quality is poor"
1. Ensure headphones are fully charged
2. Move closer to the connected device
3. Check audio codec settings (use AAC or LDAC)
4. Clean ear tips and drivers gently

Smartwatch Issues:

"Watch face is frozen"
1. Force restart: hold side button 15 seconds
2. If persistent, perform factory reset
3. Contact support if issue continues""",
        "last_updated": "2025-02-03"
    },
    {
        "id": "product-headphones-nc500",
        "title": "NC500 Noise-Cancelling Headphones",
        "category": "Product",
        "content": """Wall-E NC500 Noise-Cancelling Headphones

Overview:
The NC500 features industry-leading active noise cancellation with 
40-hour battery life and premium sound quality.

Key Features:
- Adaptive Active Noise Cancellation (ANC)
- Transparency mode for ambient awareness
- 40mm custom drivers with Hi-Res Audio support
- Bluetooth 5.2 with multipoint connection (2 devices)
- USB-C fast charging (10 min = 3 hours playback)

Controls:
- Left earcup: ANC/Transparency toggle
- Right earcup: Play/pause, volume, track skip
- Touch and hold right earcup: Voice assistant

Battery Life:
- With ANC: 30 hours
- Without ANC: 40 hours
- Full charge time: 2 hours

Audio Codecs Supported:
- SBC, AAC, aptX, aptX HD, LDAC

Comfort:
- Memory foam ear cushions
- Lightweight design (250g)
- Foldable for travel

What's in the Box:
- NC500 Headphones
- Carrying case
- USB-C charging cable
- 3.5mm audio cable
- Airplane adapter
- Quick start guide

Price: $299.99
Colors: Midnight Black, Pearl White, Navy Blue""",
        "last_updated": "2025-01-25"
    },
    {
        "id": "policy-shipping-001",
        "title": "Shipping and Delivery Policy",
        "category": "Policy",
        "content": """Wall-E Electronics Shipping Policy

Shipping Options (Continental US):

Standard Shipping:
- 5-7 business days
- Free on orders over $50
- $5.99 for orders under $50

Express Shipping:
- 2-3 business days
- $12.99 flat rate

Next-Day Shipping:
- Order by 2 PM for next business day delivery
- $24.99 flat rate
- Not available for all items

International Shipping:
- Available to 50+ countries
- 7-14 business days
- Rates calculated at checkout
- Customer responsible for duties/taxes

Order Tracking:
- Tracking number emailed within 24 hours of shipment
- Track at wall-e.com/track or carrier website

Delivery Notes:
- Signature required for orders over $500
- Apartment/unit number required for accurate delivery
- PO Boxes: Standard shipping only

Missing or Damaged Shipments:
- Report within 48 hours of delivery
- Photo evidence required for damage claims
- Replacement or refund processed within 3 business days

Holiday Shipping Deadlines:
- Check wall-e.com/holidays for seasonal cutoff dates
- Express shipping recommended during peak periods""",
        "last_updated": "2025-01-05"
    },
    {
        "id": "support-contact-001",
        "title": "Contact Support",
        "category": "Support",
        "content": """Wall-E Electronics - Contact Support

Customer Service Hours:
- Monday - Friday: 8 AM - 10 PM EST
- Saturday - Sunday: 9 AM - 6 PM EST
- Holiday hours may vary

Contact Methods:

Phone Support:
- US: 1-800-WALL-E (1-800-266-8676)
- International: +1-425-555-0100
- Average wait time: 5 minutes

Live Chat:
- Available at wall-e.com/support
- Click the chat icon in the bottom right
- AI assistant available 24/7
- Human agents during business hours

Email Support:
- support@wall-e.com
- Response within 24 hours

Social Media:
- Twitter/X: @wall-eSupport
- Facebook: facebook.com/walleelectronics
- Instagram: @wall-e_electronics

Self-Service Options:
- FAQ: wall-e.com/faq
- Community Forums: community.wall-e.com
- Video Tutorials: youtube.com/walleelectronics
- User Manuals: wall-e.com/manuals

Warranty Claims:
- warranty@wall-e.com
- Include order number and serial number

Business & Enterprise Support:
- enterprise@wall-e.com
- Dedicated account managers available""",
        "last_updated": "2025-02-01"
    }
]


def get_embedding(text: str, client: AzureOpenAI) -> list[float]:
    """Generate embedding for text using Azure OpenAI."""
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def create_search_index(index_client: SearchIndexClient):
    """Create the search index with vector search configuration."""
    
    # Define the index schema
    fields = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True),
        SearchField(name="category", type=SearchFieldDataType.String, searchable=True, filterable=True, facetable=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="last_updated", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,  # text-embedding-3-large dimension
            vector_search_profile_name="vector-profile"
        ),
    ]
    
    # Configure vector search
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="hnsw-config"),
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config",
            ),
        ],
    )
    
    # Configure semantic search
    semantic_config = SemanticConfiguration(
        name="semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
        ),
    )
    
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    # Create the index
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )
    
    # Delete existing index if it exists
    try:
        index_client.delete_index(INDEX_NAME)
        print(f"  Deleted existing index: {INDEX_NAME}")
    except Exception:
        pass
    
    # Create new index
    index_client.create_index(index)
    print(f"  Created index: {INDEX_NAME}")


def index_documents(search_client: SearchClient, openai_client: AzureOpenAI):
    """Index sample documents with embeddings."""
    
    documents_to_upload = []
    
    for doc in SAMPLE_DOCUMENTS:
        print(f"  Processing: {doc['title']}")
        
        # Generate embedding for the content
        embedding = get_embedding(doc["content"], openai_client)
        
        # Prepare document for indexing
        doc_with_vector = {
            "id": doc["id"],
            "title": doc["title"],
            "category": doc["category"],
            "content": doc["content"],
            "last_updated": doc["last_updated"],
            "content_vector": embedding
        }
        documents_to_upload.append(doc_with_vector)
    
    # Upload documents
    result = search_client.upload_documents(documents_to_upload)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"  Indexed {succeeded}/{len(documents_to_upload)} documents")


def main():
    print("=" * 60)
    print("  LLMOps Workshop - Create AI Search Index")
    print("=" * 60)
    
    # Initialize credentials
    print("\n[1/4] Authenticating with Azure...")
    credential = DefaultAzureCredential()
    print("  ✓ Using DefaultAzureCredential (RBAC)")
    
    # Initialize clients
    print("\n[2/4] Initializing clients...")
    
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        credential=credential
    )
    print(f"  ✓ Search Index Client: {AZURE_SEARCH_ENDPOINT}")
    
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential
    )
    
    openai_client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token,
        api_version="2024-02-01"
    )
    print(f"  ✓ OpenAI Client: {AZURE_OPENAI_ENDPOINT}")
    
    # Create index
    print("\n[3/4] Creating search index...")
    create_search_index(index_client)
    
    # Re-create search client after index creation
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential
    )
    
    # Index documents
    print("\n[4/4] Indexing sample documents...")
    index_documents(search_client, openai_client)
    
    print("\n" + "=" * 60)
    print("  ✓ Index creation complete!")
    print("=" * 60)
    print(f"\n  Index Name: {INDEX_NAME}")
    print(f"  Documents: {len(SAMPLE_DOCUMENTS)}")
    print(f"  Endpoint: {AZURE_SEARCH_ENDPOINT}")
    print("\n  You can now use this index in Prompt Flow for RAG!")


if __name__ == "__main__":
    main()


