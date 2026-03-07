#!/usr/bin/env python3
"""
Verify local LLM setup for Artifact Miner.

This script checks that all requirements for local LLM support are met:
1. llama-server binary is available
2. Model files are present
3. Basic inference works

Usage:
    python verify_local_llm.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from artifactminer.helpers.local_llm import (
    is_local_llm_available,
    get_local_llm_response,
    DEFAULT_MODEL,
    MODELS_DIR,
    MODEL_REGISTRY,
)


def check_llama_server():
    """Check if llama-server binary is available."""
    import shutil
    
    binary = shutil.which("llama-server")
    if binary:
        print(f"✓ llama-server found: {binary}")
        return True
    else:
        print("✗ llama-server not found on PATH")
        print("  Install instructions:")
        print("    macOS: brew install llama.cpp")
        print("    Linux: sudo apt install llama.cpp")
        print("    Windows: download from https://github.com/ggerganov/llama.cpp/releases")
        return False


def check_models_dir():
    """Check if models directory exists."""
    if MODELS_DIR.exists():
        print(f"✓ Models directory exists: {MODELS_DIR}")
        return True
    else:
        print(f"✗ Models directory not found: {MODELS_DIR}")
        print(f"  Create it with: mkdir -p {MODELS_DIR}")
        return False


def check_models():
    """Check for available model files."""
    if not MODELS_DIR.exists():
        return False
    
    gguf_files = list(MODELS_DIR.glob("*.gguf"))
    
    if not gguf_files:
        print(f"✗ No .gguf model files found in {MODELS_DIR}")
        print("  Download a model from:")
        for name, (repo_id, filename, _) in MODEL_REGISTRY.items():
            print(f"    {name}: https://huggingface.co/{repo_id}")
            print(f"      File: {filename}")
        return False
    
    print(f"✓ Found {len(gguf_files)} model file(s):")
    for gguf in gguf_files:
        # Check if it matches a known model
        matched = False
        for name, (_, filename, _) in MODEL_REGISTRY.items():
            if gguf.name == filename:
                print(f"  • {gguf.name} ({name})")
                matched = True
                break
        if not matched:
            print(f"  • {gguf.name}")
    return True


def test_inference():
    """Test basic LLM inference."""
    print("\nTesting inference...")
    
    if not is_local_llm_available(DEFAULT_MODEL):
        print(f"✗ Model '{DEFAULT_MODEL}' not available")
        return False
    
    try:
        print(f"  Using model: {DEFAULT_MODEL}")
        print("  Prompt: 'What is 2+2?'")
        print("  (This may take 30-60 seconds on first run)")
        
        response = get_local_llm_response(
            "What is 2+2? Answer in one short sentence.",
            model=DEFAULT_MODEL,
            temperature=0.1,
            max_tokens=50
        )
        
        print(f"\n  Response: {response.strip()}\n")
        print("✓ Inference successful!")
        return True
        
    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")
        return False
    except TimeoutError as e:
        print(f"✗ Timeout: {e}")
        print("  The server may be taking too long to start.")
        print("  Try a smaller/quantized model (Q4 instead of Q8)")
        return False
    except Exception as e:
        print(f"✗ Error during inference: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Artifact Miner - Local LLM Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("llama-server binary", check_llama_server),
        ("models directory", check_models_dir),
        ("model files", check_models),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())
    
    if all(results):
        print("\n" + "=" * 60)
        print("All prerequisites met! Testing inference...")
        print("=" * 60)
        inference_ok = test_inference()
        
        if inference_ok:
            print("\n" + "=" * 60)
            print("SUCCESS! Local LLM is fully functional.")
            print("=" * 60)
            print("\nYou can now:")
            print("1. Set consent level to 'full'")
            print("2. Use local LLM for repository intelligence")
            print("\nSee LOCAL_LLM_SETUP.md for more details.")
            return 0
        else:
            print("\n" + "=" * 60)
            print("PARTIAL: Prerequisites met, but inference failed.")
            print("=" * 60)
            print("\nCheck the error messages above for troubleshooting.")
            return 1
    else:
        print("\n" + "=" * 60)
        print("INCOMPLETE: Some prerequisites missing.")
        print("=" * 60)
        print("\nFollow the suggestions above to complete setup.")
        print("See LOCAL_LLM_SETUP.md for detailed instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
