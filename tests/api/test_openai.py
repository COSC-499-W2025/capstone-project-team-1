"""Integration tests for OpenAI API endpoint using real API calls."""
import os

import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here",
    reason="OPENAI_API_KEY not set in environment or using placeholder value"
)
class TestOpenAIEndpointIntegration:
    """Integration tests for the /openai POST endpoint using real OpenAI API."""

    def test_successful_openai_call(self, client):
        """Test that a valid request returns a successful response."""
        # Arrange
        payload = {"prompt": "Say 'Hello World' and nothing else."}

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
        print(f"Response: {data['response']}")

    def test_openai_call_with_multiline_prompt(self, client):
        """Test that multiline prompts are handled correctly."""
        # Arrange
        payload = {
            "prompt": """Line 1: Context
Line 2: Question
Line 3: Respond with 'Success'"""
        }

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
        print(f"Response: {data['response']}")

    def test_openai_call_with_special_characters(self, client):
        """Test that prompts with special characters are handled correctly."""
        # Arrange
        payload = {"prompt": "List these symbols: @#$%^&*(). Respond with just the symbols."}

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
        print(f"Response: {data['response']}")

    def test_very_long_prompt(self, client):
        """Test that very long prompts are handled correctly."""
        # Arrange
        long_prompt = "Count from 1 to 10 and respond with just the numbers. " + ("A" * 1000)
        payload = {"prompt": long_prompt}

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        print(f"Response: {data['response']}")

    def test_prompt_with_code_snippets(self, client):
        """Test that prompts containing code snippets work correctly."""
        # Arrange
        payload = {
            "prompt": "Review this code and respond with 'Looks good':\n```python\ndef hello():\n    print('world')\n```"
        }

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        print(f"Response: {data['response']}")


class TestOpenAIEndpointValidation:
    """Validation tests that don't require API calls."""

    def test_missing_prompt_field(self, client):
        """Test that requests without a prompt field are rejected."""
        # Arrange
        payload = {}

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data

    def test_empty_prompt_string(self, client):
        """Test endpoint behavior with an empty prompt string."""
        # Arrange
        payload = {"prompt": ""}

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Prompt cannot be empty"

    def test_whitespace_only_prompt(self, client):
        """Test that prompts containing only whitespace are rejected."""
        # Arrange
        payload = {"prompt": "   \n\t  "}

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Prompt cannot be empty"

    def test_null_prompt_value(self, client):
        """Test that null prompt values are rejected."""
        # Arrange
        payload = {"prompt": None}

        # Act
        response = client.post("/openai", json=payload)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_invalid_json_payload(self, client):
        """Test that invalid JSON payloads are rejected."""
        # Act
        response = client.post(
            "/openai",
            data="This is not valid JSON",
            headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 422
