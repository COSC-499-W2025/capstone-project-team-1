"""
GBNF grammars for llama-server constrained decoding.

Each grammar enforces a specific output structure so the model doesn't
waste tokens learning format and can't deviate from the expected layout.

These are used with ``query_llm_text(grammar=...)`` for text-based
pipeline outputs (single-stage project queries, portfolio queries).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Project section: DESCRIPTION / BULLETS / NARRATIVE
# ---------------------------------------------------------------------------

# Enforces:
#   DESCRIPTION: <one line>
#   BULLETS:
#   - <bullet line>   (2-4 bullets)
#   NARRATIVE: <one line>
PROJECT_SECTION_GRAMMAR = r"""
root        ::= description bullets narrative
description ::= "DESCRIPTION: " line "\n"
bullets     ::= "BULLETS:\n" bullet bullet bullet-opt bullet-opt
bullet      ::= "- " line "\n"
bullet-opt  ::= bullet | ""
narrative   ::= "NARRATIVE: " line "\n"
line        ::= [^\n]+
""".strip()


# ---------------------------------------------------------------------------
# Skills section: categorized skill lists
# ---------------------------------------------------------------------------

# Enforces:
#   Languages: item, item, ...
#   Frameworks & Libraries: item, item, ...
#   Tools & Infrastructure: item, item, ...
#   Practices: item, item, ...
# Each category is optional (the model can skip empty ones).
SKILLS_SECTION_GRAMMAR = r"""
root        ::= category+
category    ::= header ": " items "\n"
header      ::= "Languages" | "Frameworks & Libraries" | "Tools & Infrastructure" | "Practices"
items       ::= item (", " item)*
item        ::= [a-zA-Z0-9.+#/() -]+
""".strip()


# ---------------------------------------------------------------------------
# Summary / profile: 2-3 plain sentences
# ---------------------------------------------------------------------------

# Enforces 2-3 sentences ending with a period.
SUMMARY_GRAMMAR = r"""
root        ::= sentence " " sentence (" " sentence)?
sentence    ::= [A-Z] [^.]+ "."
""".strip()


# ---------------------------------------------------------------------------
# Bullet section: 2-4 bullet lines (micro-prompt output)
# ---------------------------------------------------------------------------

# Enforces:
#   - <bullet line>
#   - <bullet line>
#   - <bullet line>   (optional)
#   - <bullet line>   (optional)
BULLET_GRAMMAR = r"""
root       ::= bullet bullet bullet-opt bullet-opt
bullet     ::= "- " line "\n"
bullet-opt ::= bullet | ""
line       ::= [^\n]+
""".strip()

# Polish uses the same structure as draft bullets.
POLISH_BULLET_GRAMMAR = BULLET_GRAMMAR
