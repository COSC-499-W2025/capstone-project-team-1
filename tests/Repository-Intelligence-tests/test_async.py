import sys
import os
from pathlib import Path
from datetime import datetime
import pytest
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from artifactminer.helpers.openai import get_gpt5_nano_response_sync, get_gpt5_nano_response

def test_gpt5_nano_response_sync():
    time = datetime.now()
    prompt = "Summarize the following text: 'The quick brown fox jumps over the lazy dog.'"
    response = get_gpt5_nano_response_sync(prompt)
    assert isinstance(response, str)
    assert len(response) > 0
    prompt2 = "What is 2 + 2?"
    response2 = get_gpt5_nano_response_sync(prompt2)
    assert isinstance(response2, str)
    assert "4" in response2
    prompt3 = "Explain the theory of relativity in simple terms."
    response3 = get_gpt5_nano_response_sync(prompt3)
    assert isinstance(response3, str)
    time2 = datetime.now()
    print(f"Sync test duration: {(time2 - time).total_seconds()} seconds")


@pytest.mark.asyncio
async def test_gpt5_nano_response_async():
    time = datetime.now()
    
    # CONCURRENT execution - all requests happen at the same time!
    prompt1 = "Summarize the following text: 'The quick brown fox jumps over the lazy dog.'"
    prompt2 = "What is 2 + 2?"
    prompt3 = "Explain the theory of relativity in simple terms."
    
    # Using asyncio.gather to run all requests concurrently
    response, response2, response3 = await asyncio.gather(
        get_gpt5_nano_response(prompt1),
        get_gpt5_nano_response(prompt2),
        get_gpt5_nano_response(prompt3)
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert isinstance(response2, str)
    assert "4" in response2
    assert isinstance(response3, str) 
    
    time2 = datetime.now()
    print(f"Async test duration {(time2 - time).total_seconds()} seconds")