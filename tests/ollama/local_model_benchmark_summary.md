# Local LLM Benchmark Summary

## Overview
This benchmark evaluates local language models on a structured JSON generation task. The goal was to identify models that are fast, grounded, low-hallucination, and concise.

### Metrics Used
- **Mirage (lower is better):** Measures hallucination / made-up content.
- **Grounding (higher is better):** Measures how well the model sticks to provided context.
- **Redundancy (lower is better):** Measures repetition and unnecessary verbosity.
- **Seconds:** End-to-end response time on local hardware.

The ideal model for this task produces valid JSON, stays grounded, avoids hallucinations, and responds quickly.

---

## Overall Top Models
Top scoring responses from the benchmark:

1. **starcoder2:7b**
   - Score: 0.970
   - Mirage: 0.05
   - Grounding: 0.96
   - Redundancy: 0.00

2. **codellama:7b**
   - Score: 0.966
   - Mirage: 0.02
   - Grounding: 0.97
   - Redundancy: 0.05

3. **zephyr:7b**
   - Score: 0.947
   - Mirage: 0.02
   - Grounding: 0.98
   - Redundancy: 0.12

These results show that code-tuned 7B models performed best on structured output tasks.

---

## Best Small Model (≤2B)
### Winner: qwen2.5:0.5b
- Time: 3.88s
- Mirage: 0.15
- Grounding: 0.80
- Redundancy: 0.00

Notable alternatives:
- llama3.2:1b → Mirage 0.16, Grounding 0.79, Redundancy 0.00, Time 4.19s
- granite3-dense:2b → Mirage 0.18, Grounding 0.73, Redundancy 0.10, Time 10.75s

Conclusion: qwen2.5:0.5b provides the best balance of speed and grounding in the small-model category.

---

## Best Medium Model (3B–8B)
Top contenders:

| Model | Time | Mirage | Grounding | Redundancy |
|---|---|---|---|---|
| starcoder2:7b | 15.66s | 0.05 | 0.96 | 0.00 |
| codellama:7b | 18.91s | 0.02 | 0.97 | 0.05 |
| zephyr:7b | 17.97s | 0.02 | 0.98 | 0.12 |
| openchat:7b | 15.19s | 0.10 | 0.90 | 0.15 |
| dolphin-mistral:7b | 18.45s | 0.08 | 0.90 | 0.04 |

### Winner: starcoder2:7b
Reasons:
- Near-perfect grounding (0.96)
- Very low hallucination (0.05)
- Zero redundancy
- Strong response speed

Codellama:7b is a very close second, with slightly lower hallucination but slightly more verbosity.

Zephyr:7b is the best general-purpose chat model in this size range.

---

## Best Large Model (≥9B)
Top candidates:

| Model | Time | Mirage | Grounding | Redundancy |
|---|---|---|---|---|
| qwen3:14b | 44.27s | 0.39 | 0.51 | 0.00 |
| qwen2.5:14b | 47.50s | 0.40 | 0.50 | 0.05 |
| deepseek-r1:14b | 41.17s | 0.42 | 0.48 | 0.03 |
| phi4:14b | 44.28s | 0.41 | 0.49 | 0.06 |
| gemma3:12b | 30.56s | 0.48 | 0.37 | 0.07 |

### Winner: qwen3:14b
However, large models were slower and more hallucination-prone than the best 7B models on this task.

---

## Key Findings

1. Code-tuned 7B models outperform larger chat models on structured output tasks.
2. 7B models provide the best balance of speed, accuracy, and reliability.
3. Increasing parameter size above 7B did not improve performance for this benchmark.
4. Very small models (≤1B) are viable for lightweight tasks and fast responses.

---

## Recommended Local Model Stack

- Lightweight tasks: **qwen2.5:0.5b**
- Primary assistant / copilot: **starcoder2:7b**
- Optional larger model: **qwen3:14b** (not required for structured tasks)

This benchmark demonstrates that a 7B code model is the practical sweet spot for local structured-output workloads.

