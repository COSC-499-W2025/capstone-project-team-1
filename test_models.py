"""Quick model corruption test."""
from src.artifactminer.resume.llm_client import get_model, unload_model, get_available_models

models = get_available_models()
results = {}

for model_name in models:
    print(f"Testing {model_name}...", end=" ", flush=True)
    try:
        client = get_model(model_name)
        # Try a simple query
        response = client.chat.completions.create(
            model="local",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=10,
            temperature=0.0,
        )
        content = response.choices[0].message.content or ""
        unload_model()
        results[model_name] = "✓ OK"
        print("✓")
    except Exception as e:
        unload_model()
        results[model_name] = f"✗ FAILED: {str(e)[:60]}"
        print(f"✗ {str(e)[:60]}")

print("\n=== RESULTS ===")
for model, result in results.items():
    print(f"{model:25} {result}")
