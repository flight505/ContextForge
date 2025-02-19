import json
from rich.console import Console
from rich.table import Table
import subprocess
from typing import List, Dict, Any

console = Console()

TEST_CASES = [
    {
        "type": "implementation",
        "prompt": "Write a function to calculate the Fibonacci sequence up to n terms with memoization",
        "expected_features": ["memoization", "type hints", "docstring", "error handling"]
    },
    {
        "type": "debugging",
        "prompt": "Fix this code:\ndef divide(a,b): return a/b",
        "expected_features": ["type hints", "error handling", "input validation"]
    },
    {
        "type": "optimization",
        "prompt": "Optimize this function:\ndef find_duplicates(lst): return [x for x in lst if lst.count(x) > 1]",
        "expected_features": ["time complexity", "space optimization", "algorithm choice"]
    }
]

def evaluate_response(response: str, expected_features: List[str]) -> Dict[str, bool]:
    """Evaluate model response against expected features."""
    results = {}
    for feature in expected_features:
        if feature == "memoization":
            results[feature] = "@cache" in response or "memo" in response.lower()
        elif feature == "type hints":
            results[feature] = "->" in response and ":" in response
        elif feature == "error handling":
            results[feature] = "try" in response and "except" in response
        elif feature == "input validation":
            results[feature] = any(x in response.lower() for x in ["if not", "isinstance", "raise"])
        elif feature == "time complexity":
            results[feature] = "O(" in response or any(x in response.lower() for x in ["complexity", "efficient"])
    return results

def run_tests(model_path: str) -> None:
    """Run tests against the fine-tuned model."""
    table = Table(title="Model Evaluation Results")
    table.add_column("Test Type")
    table.add_column("Expected Features")
    table.add_column("Found Features")
    table.add_column("Score")
    
    for test in TEST_CASES:
        try:
            cmd = f"python -m mlx_lm.generate --model {model_path} --adapter-path docstring_adapter"
            response = subprocess.run(
                cmd,
                shell=True,
                input=test["prompt"],
                capture_output=True,
                text=True
            ).stdout
            
            results = evaluate_response(response, test["expected_features"])
            score = sum(results.values()) / len(results)
            
            table.add_row(
                test["type"],
                ", ".join(test["expected_features"]),
                ", ".join(k for k, v in results.items() if v),
                f"{score:.2%}"
            )
        except Exception as e:
            console.print(f"[red]Error running test {test['type']}: {str(e)}[/red]")
    
    console.print(table)

if __name__ == "__main__":
    run_tests("mlx-community/DeepSeek-R1-Distill-Qwen-1.5B") 