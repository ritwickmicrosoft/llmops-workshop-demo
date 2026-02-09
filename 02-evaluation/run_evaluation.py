"""
LLMOps Workshop - Evaluation Script
====================================
Runs evaluation metrics on the RAG chatbot using Azure AI Foundry Evaluation SDK.
Uses built-in evaluators: Groundedness, Relevance, Coherence, Fluency.

Authentication: DefaultAzureCredential (RBAC - no API keys)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import (
    GroundednessEvaluator,
    RelevanceEvaluator,
    CoherenceEvaluator,
    FluencyEvaluator,
    evaluate,
)
from azure.ai.projects import AIProjectClient


# Configuration
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
AZURE_RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "rg-llmops-demo")
AZURE_PROJECT_NAME = os.environ.get("AZURE_PROJECT_NAME", "aiproj-llmops-dev")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

EVAL_DATA_PATH = Path(__file__).parent / "eval_dataset.jsonl"
RESULTS_PATH = Path(__file__).parent / "eval_results"


def load_evaluation_data(file_path: Path) -> list[dict]:
    """Load evaluation dataset from JSONL file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def run_rag_flow(question: str, project_client: AIProjectClient) -> dict:
    """
    Run the RAG flow and return the response.
    In a real scenario, this would call the deployed Prompt Flow endpoint.
    """
    # This is a placeholder - in production, call your deployed endpoint
    # For demo purposes, we'll use the chat completion directly
    
    from openai import AzureOpenAI
    
    credential = DefaultAzureCredential()
    
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-02-01"
    )
    
    # Simulate RAG response (in production, this calls your Prompt Flow endpoint)
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You are a helpful customer support assistant for Wall-E Electronics."},
            {"role": "user", "content": question}
        ],
        max_tokens=500,
        temperature=0.3
    )
    
    return {
        "response": response.choices[0].message.content,
        "context": ""  # Would come from RAG retrieval
    }


def main():
    print("=" * 60)
    print("  LLMOps Workshop - RAG Evaluation")
    print("=" * 60)
    
    # Validate environment
    if not AZURE_OPENAI_ENDPOINT:
        print("\n⚠️  AZURE_OPENAI_ENDPOINT not set. Using default.")
    
    # Initialize credentials
    print("\n[1/5] Authenticating with Azure...")
    credential = DefaultAzureCredential()
    print("  ✓ Using DefaultAzureCredential (RBAC)")
    
    # Load evaluation data
    print("\n[2/5] Loading evaluation dataset...")
    eval_data = load_evaluation_data(EVAL_DATA_PATH)
    print(f"  ✓ Loaded {len(eval_data)} evaluation samples")
    
    # Initialize evaluators
    print("\n[3/5] Initializing evaluators...")
    
    model_config = {
        "azure_endpoint": AZURE_OPENAI_ENDPOINT,
        "azure_deployment": AZURE_OPENAI_DEPLOYMENT,
        "api_version": "2024-02-01"
    }
    
    evaluators = {
        "groundedness": GroundednessEvaluator(model_config=model_config),
        "relevance": RelevanceEvaluator(model_config=model_config),
        "coherence": CoherenceEvaluator(model_config=model_config),
        "fluency": FluencyEvaluator(model_config=model_config),
    }
    print(f"  ✓ Initialized {len(evaluators)} evaluators")
    
    # Prepare evaluation data
    print("\n[4/5] Running evaluation...")
    
    # Format data for evaluation
    evaluation_rows = []
    for item in eval_data:
        row = {
            "question": item["question"],
            "ground_truth": item["ground_truth"],
            "context": item.get("context", ""),
            # In production, get actual response from your deployed flow
            "response": item["ground_truth"]  # Placeholder for demo
        }
        evaluation_rows.append(row)
    
    # Run evaluation
    results = evaluate(
        data=evaluation_rows,
        evaluators=evaluators,
        evaluator_config={
            "groundedness": {
                "question": "${data.question}",
                "context": "${data.context}",
                "response": "${data.response}"
            },
            "relevance": {
                "question": "${data.question}",
                "response": "${data.response}"
            },
            "coherence": {
                "response": "${data.response}"
            },
            "fluency": {
                "response": "${data.response}"
            }
        }
    )
    
    # Process and display results
    print("\n[5/5] Processing results...")
    
    # Create results directory
    RESULTS_PATH.mkdir(exist_ok=True)
    
    # Calculate aggregate metrics
    metrics = results.get("metrics", {})
    
    print("\n" + "=" * 60)
    print("  Evaluation Results")
    print("=" * 60)
    
    print("\n  Aggregate Metrics:")
    print("  " + "-" * 40)
    
    metric_names = ["groundedness", "relevance", "coherence", "fluency"]
    for metric in metric_names:
        value = metrics.get(f"mean_{metric}", metrics.get(metric, "N/A"))
        if isinstance(value, float):
            # Color code based on score (1-5 scale)
            if value >= 4.0:
                status = "✓"
            elif value >= 3.0:
                status = "~"
            else:
                status = "✗"
            print(f"  {status} {metric.capitalize():15} {value:.2f}/5.0")
        else:
            print(f"    {metric.capitalize():15} {value}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_PATH / f"eval_results_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "dataset_size": len(eval_data),
            "metrics": metrics,
            "rows": results.get("rows", [])
        }, f, indent=2)
    
    print(f"\n  ✓ Detailed results saved to: {results_file}")
    
    print("\n" + "=" * 60)
    print("  Evaluation Complete!")
    print("=" * 60)
    
    # Recommendations
    print("\n  📊 Recommendations:")
    for metric in metric_names:
        value = metrics.get(f"mean_{metric}", 0)
        if isinstance(value, float) and value < 4.0:
            print(f"  - Consider improving {metric}: current score {value:.2f}")
    
    print("\n  Next Steps:")
    print("  1. Review low-scoring responses in detailed results")
    print("  2. Iterate on prompts or retrieval strategy")
    print("  3. Re-run evaluation to measure improvements")


if __name__ == "__main__":
    main()

