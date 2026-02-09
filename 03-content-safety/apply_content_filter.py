"""
LLMOps Workshop - Apply Content Safety Filter
==============================================
Applies custom content filter configuration to Azure OpenAI deployment.

This script demonstrates how to programmatically configure content safety.
In production, you would typically use the Azure Portal or ARM/Bicep templates.

Authentication: DefaultAzureCredential (RBAC)
"""

import os
import json
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient


# Configuration
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
AZURE_RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "rg-llmops-demo")
AZURE_OPENAI_ACCOUNT = os.environ.get("AZURE_OPENAI_ACCOUNT", "aoai-llmops-dev")
DEPLOYMENT_NAME = "gpt-4o"

CONFIG_PATH = Path(__file__).parent / "content_filter_config.json"


def load_filter_config(config_path: Path) -> dict:
    """Load content filter configuration from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print("=" * 60)
    print("  LLMOps Workshop - Apply Content Safety Filter")
    print("=" * 60)
    
    # Validate environment
    if not AZURE_SUBSCRIPTION_ID:
        print("\n❌ AZURE_SUBSCRIPTION_ID environment variable not set.")
        print("   Run: $env:AZURE_SUBSCRIPTION_ID = '<your-subscription-id>'")
        return
    
    # Initialize credentials
    print("\n[1/4] Authenticating with Azure...")
    credential = DefaultAzureCredential()
    print("  ✓ Using DefaultAzureCredential (RBAC)")
    
    # Initialize management client
    print("\n[2/4] Initializing Cognitive Services client...")
    client = CognitiveServicesManagementClient(
        credential=credential,
        subscription_id=AZURE_SUBSCRIPTION_ID
    )
    print(f"  ✓ Subscription: {AZURE_SUBSCRIPTION_ID}")
    
    # Load filter configuration
    print("\n[3/4] Loading content filter configuration...")
    filter_config = load_filter_config(CONFIG_PATH)
    print(f"  ✓ Filter name: {filter_config['name']}")
    print(f"  ✓ Base policy: {filter_config['basePolicyName']}")
    
    # Display filter settings
    print("\n  Input Filters:")
    for key, value in filter_config['inputFilters'].items():
        if value.get('filterEnabled'):
            threshold = value.get('severityThreshold', 'N/A')
            print(f"    - {key}: {threshold}")
    
    print("\n  Output Filters:")
    for key, value in filter_config['outputFilters'].items():
        if value.get('filterEnabled'):
            threshold = value.get('severityThreshold', 'Enabled')
            print(f"    - {key}: {threshold}")
    
    # Get current deployment
    print(f"\n[4/4] Applying filter to deployment '{DEPLOYMENT_NAME}'...")
    
    try:
        deployment = client.deployments.get(
            resource_group_name=AZURE_RESOURCE_GROUP,
            account_name=AZURE_OPENAI_ACCOUNT,
            deployment_name=DEPLOYMENT_NAME
        )
        print(f"  ✓ Found deployment: {deployment.name}")
        print(f"  ✓ Model: {deployment.properties.model.name}")
        
        # Note: Programmatic content filter application requires specific API
        # For workshop purposes, we guide users to apply via Portal
        print("\n" + "=" * 60)
        print("  ⚠️  Content Filter Application")
        print("=" * 60)
        print("""
  To apply the content filter configuration:
  
  1. Open Azure AI Foundry Portal: https://ai.azure.com
  2. Navigate to your project → Safety + security → Content filters
  3. Click 'Create content filter'
  4. Configure settings as shown above
  5. Apply to your gpt-4o deployment
  
  Alternatively, use the Azure Portal:
  1. Go to your Azure OpenAI resource
  2. Click 'Content filters' under Resource Management
  3. Create a new content filter with the settings above
  4. Assign it to your deployment
""")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Make sure the deployment exists and you have proper permissions.")
        return
    
    print("\n  ✓ Content filter configuration ready for application!")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
