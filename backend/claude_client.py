import os
from typing import Any, Dict, Optional, TypeVar, Union

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Model constants
CLAUDE_OPUS = "claude-opus-4-20250514"
CLAUDE_SONNET = "claude-sonnet-4-20250514"
CLAUDE_HAIKU = "claude-3-5-haiku-20241022"
DEFAULT_MODEL = CLAUDE_SONNET

load_dotenv()


class ClaudeResponse(BaseModel):
    """Base model for Claude responses"""

    content: Union[str, Dict[str, Any]]
    model: str
    usage: Optional[Dict[str, Any]] = None


class ClaudeClient:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.client = Anthropic(api_key=api_key)

    def get_completion(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        system_message: Optional[str] = None,
        temperature: float = 1.0,
    ) -> ClaudeResponse:
        """
        Get a simple completion from Claude

        Args:
            prompt: The input prompt
            model: The model to use (default: claude-sonnet-4)
            max_tokens: Maximum tokens in response (default: 4096)
            system_message: Optional system message to guide the model
            temperature: Temperature for response randomness (0.0-1.0)

        Returns:
            ClaudeResponse with content and metadata
        """
        try:
            # Prepare parameters
            params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_message:
                params["system"] = system_message

            # Make the API call
            response = self.client.messages.create(**params)

            # Extract the response
            content = response.content[0].text if response.content else ""
            model_used = response.model
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

            return ClaudeResponse(content=content, model=model_used, usage=usage)

        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    def get_structured_completion(
        self,
        prompt: str,
        pydantic_model: type[T],
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        system_message: Optional[str] = None,
        temperature: float = 1.0,
    ) -> T:
        """
        Get a structured response from Claude with Pydantic validation

        Args:
            prompt: The input prompt
            pydantic_model: Pydantic model class for structured output
            model: The model to use (default: claude-sonnet-4)
            max_tokens: Maximum tokens in response
            system_message: Optional system message to guide the model
            temperature: Temperature for response randomness (0.0-1.0)

        Returns:
            Parsed Pydantic model instance
        """
        try:
            import json

            # Add JSON formatting instructions to the prompt
            json_prompt = f"""{prompt}

Please respond with a valid JSON object that matches this structure:
{pydantic_model.model_json_schema()}

Return ONLY the JSON object, no additional text."""

            # Prepare parameters
            params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": json_prompt}],
            }

            if system_message:
                params["system"] = system_message

            # Make the API call
            response = self.client.messages.create(**params)

            # Extract and parse the response
            content = response.content[0].text if response.content else "{}"

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON and validate with Pydantic
            parsed_data = json.loads(content)
            return pydantic_model.model_validate(parsed_data)

        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    def analyze_image_with_vision(
        self,
        prompt: str,
        pydantic_model: type[T],
        image_path: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        system_message: Optional[str] = None,
        temperature: float = 1.0,
    ) -> T:
        """
        Analyze an image using Claude's vision capabilities with structured output

        Args:
            prompt: The prompt describing what to analyze in the image
            pydantic_model: Pydantic model class for structured output
            image_path: Path to the image file
            model: The vision model to use (default: claude-sonnet-4)
            max_tokens: Maximum tokens in response
            system_message: Optional system message to guide the model
            temperature: Temperature for response randomness (0.0-1.0)

        Returns:
            Parsed Pydantic model instance
        """
        try:
            import base64
            import json
            import mimetypes

            # Read and encode the image
            with open(image_path, "rb") as image_file:
                image_data = base64.standard_b64encode(image_file.read()).decode("utf-8")

            # Determine the media type
            media_type, _ = mimetypes.guess_type(image_path)
            if not media_type or not media_type.startswith("image/"):
                media_type = "image/jpeg"  # Default fallback

            # Add JSON formatting instructions to the prompt
            json_prompt = f"""{prompt}

Please respond with a valid JSON object that matches this structure:
{pydantic_model.model_json_schema()}

Return ONLY the JSON object, no additional text."""

            # Prepare the message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": json_prompt},
                    ],
                }
            ]

            # Prepare parameters
            params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_message:
                params["system"] = system_message

            # Make the API call
            response = self.client.messages.create(**params)

            # Extract and parse the response
            content = response.content[0].text if response.content else "{}"

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON and validate with Pydantic
            parsed_data = json.loads(content)
            return pydantic_model.model_validate(parsed_data)

        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    def get_streaming_completion(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        system_message: Optional[str] = None,
        temperature: float = 1.0,
    ):
        """
        Get a streaming completion from Claude

        Args:
            prompt: The input prompt
            model: The model to use (default: claude-sonnet-4)
            max_tokens: Maximum tokens in response
            system_message: Optional system message to guide the model
            temperature: Temperature for response randomness (0.0-1.0)

        Yields:
            Chunks of text as they're generated
        """
        try:
            # Prepare parameters
            params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_message:
                params["system"] = system_message

            # Make the streaming API call
            with self.client.messages.stream(**params) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            raise Exception(f"Claude API streaming error: {str(e)}")


# Global instance
try:
    claude_client = ClaudeClient()
except ValueError as e:
    print(f"Warning: Claude client not initialized: {e}")
    claude_client = None

