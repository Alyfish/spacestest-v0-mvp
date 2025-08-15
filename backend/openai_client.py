import os
from typing import Any, Dict, Optional, TypeVar, Union

from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Model constants
GPT_5 = "gpt-5"
GPT_5_MINI = "gpt-5-mini"
GPT_5_NANO = "gpt-5-nano"
DEFAULT_MODEL = GPT_5_NANO


class OpenAIResponse(BaseModel):
    """Base model for OpenAI responses"""

    content: Union[str, Dict[str, Any]]
    model: str
    usage: Optional[Dict[str, Any]] = None


class OpenAIClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=api_key)

    def get_completion(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> OpenAIResponse:
        """
        Get a simple completion from OpenAI

        Args:
            prompt: The input prompt
            model: The model to use (default: gpt-5-nano)
            max_tokens: Maximum tokens in response
            response_format: Format for structured responses (e.g., {"type": "json_object"})

        Returns:
            OpenAIResponse with content and metadata
        """
        try:
            messages = [{"role": "user", "content": prompt}]

            # Prepare parameters
            params = {
                "model": model,
                "messages": messages,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            if response_format:
                params["response_format"] = response_format

            # Make the API call
            response: ChatCompletion = self.client.chat.completions.create(**params)

            # Extract the response
            content = response.choices[0].message.content
            model_used = response.model
            usage = response.usage.model_dump() if response.usage else None

            return OpenAIResponse(content=content, model=model_used, usage=usage)

        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    def get_structured_completion(
        self,
        prompt: str,
        pydantic_model: type[T],
        model: str = DEFAULT_MODEL,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
    ) -> T:
        """
        Get a structured response from OpenAI using the new responses.parse method with Pydantic validation

        Args:
            prompt: The input prompt
            pydantic_model: Pydantic model class for structured output
            model: The model to use (default: gpt-5-nano)
            max_tokens: Maximum tokens in response
            system_message: Optional system message to guide the model

        Returns:
            Parsed Pydantic model instance
        """
        try:
            # Prepare input messages
            input_messages = []

            if system_message:
                input_messages.append({"role": "system", "content": system_message})

            input_messages.append({"role": "user", "content": prompt})

            # Prepare parameters
            params = {
                "model": model,
                "input": input_messages,
                "text_format": pydantic_model,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Make the API call using the new responses.parse method
            response = self.client.responses.parse(**params)

            # Return the parsed Pydantic model
            return response.output_parsed

        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


# Global instance
try:
    openai_client = OpenAIClient()
except ValueError as e:
    print(f"Warning: OpenAI client not initialized: {e}")
    openai_client = None
