#Part of the Repository Intelligence Module
#Owner: Evan/van-cpu

import asyncio
from typing import List
from artifactminer.db.models import Consent, UserAIntelligenceSummary
from artifactminer.db.database import SessionLocal
from artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo, Pathish
from artifactminer.helpers.openai import get_gpt5_nano_response
from artifactminer.helpers.ollama import get_ollama_response


def get_user_llm_selection() -> str:
    db = SessionLocal() #create a new database session
    try:
        consent = db.get(Consent, 1)
        if consent is None: #no consent row means default to ollama
            consent = db.query(Consent).order_by(Consent.id.desc()).first() #get the latest consent row if multiple exist
        return consent.LLM_model if consent and consent.LLM_model else "chatGPT"#return user's LLM selection or default to "chatGPT"
    except Exception as e:
        print(f"An error occurred: {e}")
        return "chatGPT"
                
def set_user_llm_selection(model: str):
    db = SessionLocal()
    try:
        consent = db.get(Consent, 1)
        if consent:
            consent.LLM_model = model
        else:
            consent = Consent(id=1, consent_level="none", LLM_model=model)
        db.merge(consent)   # merge = insert or update
        db.commit()
    finally:
        db.close()

async def getLLMResponse(prompt: str) -> str:
    if get_user_llm_selection() == "chatGPT":
        return await get_gpt5_nano_response(prompt)
    else:
        return get_ollama_response(prompt)

# Check if user has allowed LLM usage via consent
def user_allows_llm() -> bool:
    db = SessionLocal() #create a new database session
    try:
        consent = db.get(Consent, 1)
        if consent is None: #no consent row means no consent given
            consent = db.query(Consent).order_by(Consent.id.desc()).first() #get the latest consent row if multiple exist
        return bool(consent and (consent.consent_level or "").lower() == "full")#return True if consent level is "full"
    finally:
        db.close()
# Set user consent level for LLM usage
def set_user_consent(level: str):
    db = SessionLocal()
    try:
        consent = Consent(id=1, consent_level=level)
        db.merge(consent)   # merge = insert or update
        db.commit()
    finally:
        db.close()

from typing import List

#The goal of this function is to take a list of commit additions (each a string) and merge them into at most `max_blocks` strings, each no longer than `max_chars_per_block` characters.
#basically to limit the stress on the LLM by chunking the input into manageable pieces.
def group_additions_into_blocks(
    additions: List[str],
    max_blocks: int = 5,
    max_chars_per_block: int = 8000,) -> List[str]:
    """Take a list of commit additions (each a string) and merge them into
    at most `max_blocks` strings."""
    blocks: List[str] = []
    current = ""

    for addition in additions:
        # stop if we already filled all blocks
        if len(blocks) >= max_blocks:
            break

        # what it would look like if we add this commit to current
        candidate = (current + "\n\n" + addition) if current else addition

        if len(candidate) <= max_chars_per_block:
            # still fits, keep growing current block
            current = candidate
        else:
            # current has content, close it out
            if current:
                blocks.append(current)
                if len(blocks) >= max_blocks:
                    break
                # start new block with this addition (maybe truncated)
                current = addition[:max_chars_per_block]
            else:
                # single huge commit: just take a truncated version as its own block
                blocks.append(addition[:max_chars_per_block])

    # push the last block if there's room
    if current and len(blocks) < max_blocks:
        blocks.append(current)

    return blocks


# Create a summary of user additions using LLM
async def createAIsummaryFromUserAdditions(additions: List[str]) -> str:
    #Each addition in additions is a string of added lines from a single commit
    if not additions:
        return "No additions found for the specified user."
    if not user_allows_llm():
        return "User has not consented to LLM usage."
    
    # Build all prompts for concurrent execution
    prompts = []
    for addition in additions:
        prompt = (
        "You are evaluating a student's code contribution from a single commit. "
        "Your job is to identify and articulate the *strengths* demonstrated in the added lines. "
        "Focus only on positive, portfolio-ready highlights. "
        "Do not mention weaknesses, omissions, inconsistencies, errors, or anything negative. "

        "For this commit, highlight: "
        "- Functional impact: what the change enables or improves "
        "- Technical skills demonstrated (OOP, data structures, algorithms, async patterns, etc.) "
        "- Software engineering competencies (clean architecture, modularity, documentation-quality, tests, type safety) "
        "- Performance or reliability improvements implied by the change "
        "- Indicators of good development practices (readability, maintainability, clarity, structure) "

        "Constraints: "
        "- Produce 4–6 concise bullet points "
        "- No criticism or negativity "
        "- No speculation beyond what's visible in the diff "
        "- Do not restate the code; describe the skill it implies "

        "ADDED LINES (unified diff subset, additions only):\n"
        )
        prompt += f"{addition}\n\n"
        prompts.append(prompt)
    
    # Execute all LLM calls concurrently
    intermediate_summaries = await asyncio.gather(*[getLLMResponse(p) for p in prompts])
    intermediate_summary = "".join(intermediate_summaries)

    final_summary = "LLM model used: " + get_user_llm_selection() + "\n\n" + await getLLMResponse(
    "Create a polished, portfolio-ready summary of this student's overall code contributions. "
    "Only highlight strengths, technical skills, and positive impact. "
    "Do not mention weaknesses, issues, inconsistencies, or anything negative. "
    "Focus on themes such as engineering maturity, problem-solving ability, code quality, "
    "architecture decisions, and demonstrated competencies. "
    "Keep the tone professional and achievement-oriented. "
    "Be concise and produce a cohesive paragraph or a short set of strong bullets. "
    "Here are the aggregated commit analyses:\n\n"
    + intermediate_summary
)

    return final_summary


# Create a summary of user additions using LLM if consented and without LLM if not
async def createSummaryFromUserAdditions(additions: List[str]) -> str:
    summary: str
    if not additions:
        return "No additions found for the specified user."
    if not user_allows_llm():
        #User has not consented to LLM usage we will create a summary without LLM, placeholder for now
        summary = "User has not consented to LLM usage. Summary generation without LLM is not yet implemented."
    else:
        #User has consented to LLM usage we will create a summary with LLM
        summary = await createAIsummaryFromUserAdditions(additions)
    return summary


def saveUserIntelligenceSummary(repo_path: str, user_email: str, summary_text: str):
    db = SessionLocal()
    try:
        user_summary = UserAIntelligenceSummary(
            repo_path=repo_path,
            user_email=user_email,
            summary_text=summary_text,
        )
        db.add(user_summary)
        db.commit()
        db.refresh(user_summary)
    finally:
        db.close()