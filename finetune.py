#!/usr/bin/env python3
import ast
import json
import os
import random
import shutil
import subprocess
import tempfile
from typing import Dict, List

import vertexai

# Vertex AI imports
from rich.console import Console
from vertexai.language_models import TextGenerationModel
from vertexai.preview.generative_models import GenerativeModel

# Initialize Rich console for better error messages
console = Console()

# ---------- CONFIGURATION ----------
# Repository URLs
REPO_URL = "https://github.com/unit8co/darts"
# Output directory for training data
DATA_DIR = "./data"
TRAIN_FILE = os.path.join(DATA_DIR, "train.jsonl")
VALID_FILE = os.path.join(DATA_DIR, "valid.jsonl")
# Percentage split for training (e.g., 90% train, 10% valid)
TRAIN_SPLIT = 0.9
# MLX fine-tuning command template
MLX_CMD = (
    "mlx_lm.lora --model mlx-community/DeepSeek-R1-Distill-Qwen-1.5B "
    "--train --data ./data --iters 100 "
    "--batch-size 4 --learning-rate 1e-4 "
    "--steps-per-report 10 --steps-per-eval 50 "
    "--val-batches 20 --adapter-path docstring_adapter"
)

try:
    # Initialize Vertex AI with project and location from environment variables
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
    
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
    
    # Initialize Vertex AI
    vertexai.init(project=project_id, location=location)
    
    # Initialize the Gemini model for code generation
    model = GenerativeModel("gemini-1.0-pro")
    
    # Also initialize a code-specific model as backup
    code_model = TextGenerationModel.from_pretrained("code-bison@002")
    
    console.print("[green]Successfully initialized Vertex AI models[/green]")
except Exception as e:
    console.print(f"[red]Error initializing Vertex AI: {str(e)}[/red]")
    console.print("[yellow]Please ensure you have:")
    console.print("1. Set GOOGLE_CLOUD_PROJECT environment variable")
    console.print("2. Set GOOGLE_CLOUD_LOCATION environment variable (defaults to us-central1)")
    console.print("3. Authenticated: gcloud auth application-default login")
    console.print("4. Enabled Vertex AI API: gcloud services enable aiplatform.googleapis.com[/yellow]")
    raise

def clone_repository(repo_url: str, dest_dir: str) -> None:
    """Clone the given repository URL into dest_dir."""
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    subprocess.run(["git", "clone", repo_url, dest_dir], check=True)
    print(f"Cloned repository into {dest_dir}")

def run_contextforge(repo_path: str, output_json: str) -> None:
    """Run ContextForge on the repo_path and write JSONL output to output_json."""
    cmd = ["contextforge", repo_path, "-l", "-o", output_json]
    subprocess.run(cmd, check=True)
    print(f"ContextForge output written to {output_json}")

async def enhance_qa_pair(prompt: str, completion: str) -> List[Dict[str, str]]:
    """Use Vertex AI to enhance Q/A pairs with variations."""
    # Combine system prompt and context into a single user message
    system_prompt = """You are an expert Python developer creating training data for a code assistant.
    Given a function and its docstring, create 4-5 diverse training examples that cover:
    1. Code corrections (e.g., fixing bugs, improving error handling)
    2. Natural language to code transformations
    3. Framework additions (e.g., adding type hints, logging, testing)
    4. Code optimizations with explanations
    5. Multi-turn debugging conversations

    Return only in this format:
    TYPE: <type of example>
    Q: <question/prompt>
    A: <detailed answer with code>"""
    
    context = f"Function:\n{completion}\n\nDocstring:\n{prompt}"
    full_prompt = f"{system_prompt}\n\nNow analyze this:\n{context}"
    
    try:
        # Try with Gemini Pro first
        response = model.generate_content(
            full_prompt,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            },
            safety_settings={
                "harassment": "block_none",
                "hate_speech": "block_none",
                "sexually_explicit": "block_none",
                "dangerous_content": "block_none"
            }
        )
        
        if not response.text:
            raise ValueError("Empty response from Gemini model")
            
    except Exception as e:
        console.print(f"[yellow]Gemini model failed: {str(e)}. Falling back to Code Bison...[/yellow]")
        try:
            # Fallback to Code Bison
            response = code_model.predict(
                full_prompt,
                temperature=0.7,
                max_output_tokens=8192,
                top_k=40,
                top_p=0.95,
            )
            if not response.text:
                raise ValueError("Empty response from Code Bison model")
        except Exception as fallback_e:
            console.print(f"[red]Both models failed. Error: {str(fallback_e)}[/red]")
            return []
    
    qa_pairs = []
    current_type = None
    current_q = None
    current_a = None
    
    try:
        for line in response.text.split('\n'):
            if line.startswith('TYPE:'):
                if current_q and current_a:
                    qa_pairs.append({
                        "prompt": f"[{current_type}] {current_q.strip()}", 
                        "completion": current_a.strip()
                    })
                current_type = line[5:].strip()
                current_q = None
                current_a = None
            elif line.startswith('Q:'):
                if current_q and current_a:
                    qa_pairs.append({
                        "prompt": f"[{current_type}] {current_q.strip()}", 
                        "completion": current_a.strip()
                    })
                current_q = line[2:].strip()
                current_a = None
            elif line.startswith('A:'):
                current_a = line[2:].strip()
        
        # Don't forget the last pair
        if current_type and current_q and current_a:
            qa_pairs.append({
                "prompt": f"[{current_type}] {current_q.strip()}", 
                "completion": current_a.strip()
            })
    except Exception as parse_e:
        console.print(f"[red]Error parsing model response: {str(parse_e)}[/red]")
        return []
    
    return qa_pairs

async def extract_qa_pairs_from_python(json_file: str) -> List[Dict[str, str]]:
    """Parse the ContextForge JSONL output and extract coding examples."""
    qa_pairs = []
    files = []
    
    # Read JSONL format
    with open(json_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                file_data = json.loads(line.strip())
                if isinstance(file_data, dict) and "path" in file_data and "content" in file_data:
                    files.append(file_data)
            except json.JSONDecodeError:
                continue

    # Process each file
    for file in files:
        if not file["path"].endswith(".py"):
            continue
        try:
            tree = ast.parse(file["content"])
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_source = ast.get_source_segment(file["content"], node)
                if func_source:
                    docstring = ast.get_docstring(node, clean=True)
                    if docstring:
                        # Create implementation example
                        prompt = f"Implement a Python function based on this description:\n{docstring}"
                        completion = func_source.strip()
                        qa_pairs.append({"prompt": prompt, "completion": completion})
                        
                        # Create docstring example
                        prompt = f"Write a detailed docstring for the following function:\n\n{func_source.strip()}"
                        qa_pairs.append({"prompt": prompt, "completion": docstring.strip()})
                        
                        # Add enhanced Q/A pairs using Vertex AI
                        enhanced_pairs = await enhance_qa_pair(docstring, func_source)
                        qa_pairs.extend(enhanced_pairs)

    return qa_pairs

def split_and_write_dataset(qa_pairs: List[Dict[str, str]], train_file: str, valid_file: str, train_split: float = 0.9) -> None:
    """Shuffle and split qa_pairs into training and validation sets."""
    random.shuffle(qa_pairs)
    split_idx = int(len(qa_pairs) * train_split)
    train_data = qa_pairs[:split_idx]
    valid_data = qa_pairs[split_idx:]
    
    os.makedirs(os.path.dirname(train_file), exist_ok=True)
    with open(train_file, "w", encoding="utf-8") as tf:
        for entry in train_data:
            tf.write(json.dumps(entry) + "\n")
    with open(valid_file, "w", encoding="utf-8") as vf:
        for entry in valid_data:
            vf.write(json.dumps(entry) + "\n")
            
    print(f"Wrote {len(train_data)} training examples to {train_file}")
    print(f"Wrote {len(valid_data)} validation examples to {valid_file}")

async def main():
    # Create a temporary directory for cloning the repo and ContextForge output
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = os.path.join(temp_dir, "darts")
        output_json = os.path.join(temp_dir, "darts_context.json")
        
        # 1. Clone the repository
        clone_repository(REPO_URL, repo_dir)
        
        # 2. Run ContextForge on the repository to produce JSON output
        run_contextforge(repo_dir, output_json)
        
        # 3. Extract Q/A pairs from the JSON output
        qa_pairs = await extract_qa_pairs_from_python(output_json)
        if not qa_pairs:
            print("No QA pairs extracted. Check if the repository contains Python files with functions and docstrings.")
            return
            
        # 4. Split and write dataset to disk
        split_and_write_dataset(qa_pairs, TRAIN_FILE, VALID_FILE, TRAIN_SPLIT)
    
    # 5. Print the MLX fine-tuning command
    print("\nDataset is ready. To fine-tune using MLX with LoRA, run the following command:")
    print(MLX_CMD)
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())