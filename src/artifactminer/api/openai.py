"""
OpenAI API module: endpoints for interacting with OpenAI models.
"""

from fastapi import APIRouter, HTTPException
from .schemas import OpenAIRequest, OpenAIResponse
from ..helpers.openai import get_gpt5_nano_response


router = APIRouter(tags=["openai"])


@router.post("/openai", response_model=OpenAIResponse)
async def call_openai(request: OpenAIRequest) -> OpenAIResponse:
    """Call the OpenAI API with the provided prompt and return the response."""
    # Validate that prompt is not empty or just whitespace
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty")

    try:
        response_text = get_gpt5_nano_response(request.prompt)
        return OpenAIResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get response from OpenAI API") from e
