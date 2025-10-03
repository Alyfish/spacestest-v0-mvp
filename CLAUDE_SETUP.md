# Claude Code Setup Guide

This guide will help you set up Claude Code and the Anthropic API for this project.

## Prerequisites

- Node.js installed (v16 or higher)
- An Anthropic API key ([Get one here](https://console.anthropic.com/))

## Installation

The `@anthropic-ai/claude-code` package has been installed locally in this project. You can use it via npx commands.

## Setup Steps

### 1. Get Your Anthropic API Key

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Then edit the `.env` file and add your Anthropic API key:

```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

### 3. Initialize Claude Code (Optional)

If you want to use the Claude Code CLI tool:

```bash
npx @anthropic-ai/claude-code init
```

This will:
- Ask for permission to access the directory
- Set up Claude Code configuration
- Allow you to use Claude via the CLI

### 4. Test the Python Claude Client

The project includes a Python client for Claude API at `backend/claude_client.py`.

To test it:

```bash
cd backend
python3 -c "from claude_client import claude_client; print(claude_client.get_completion('Hello, Claude!').content)"
```

## Usage

### Python Client

```python
from claude_client import claude_client

# Simple completion
response = claude_client.get_completion(
    prompt="Analyze this room layout",
    model="claude-sonnet-4-20250514"
)
print(response.content)

# Structured output with Pydantic
from pydantic import BaseModel

class RoomAnalysis(BaseModel):
    space_type: str
    style: str
    recommendations: list[str]

analysis = claude_client.get_structured_completion(
    prompt="Analyze this bedroom: modern, minimalist, needs lighting",
    pydantic_model=RoomAnalysis
)

# Vision analysis
result = claude_client.analyze_image_with_vision(
    prompt="What improvements can be made to this room?",
    pydantic_model=RoomAnalysis,
    image_path="path/to/image.jpg"
)
```

### Claude Code CLI

```bash
# Start a conversation
npx @anthropic-ai/claude-code

# Run with a specific prompt
npx @anthropic-ai/claude-code "Help me refactor this code"

# Use with files
npx @anthropic-ai/claude-code "Review backend/main.py for improvements"
```

## Available Claude Models

The client supports these models:

- **claude-opus-4-20250514** - Most capable, best for complex tasks
- **claude-sonnet-4-20250514** - Balanced performance and speed (default)
- **claude-3-5-haiku-20241022** - Fastest, good for simple tasks

## Features

### Python Client Features

✅ Simple text completions  
✅ Structured JSON output with Pydantic validation  
✅ Vision/image analysis  
✅ Streaming responses  
✅ Custom system messages  
✅ Temperature control  
✅ Token usage tracking  

### Claude Code CLI Features

✅ Interactive chat with Claude  
✅ File reading and editing  
✅ Code generation and refactoring  
✅ Command execution  
✅ Project-aware context  

## API Cost Optimization

- Use **Haiku** for simple tasks (cheapest)
- Use **Sonnet** for most work (balanced)
- Use **Opus** only for complex reasoning (most expensive)

## Troubleshooting

### "ANTHROPIC_API_KEY not found" Error

Make sure you've:
1. Created a `.env` file in the root directory
2. Added your API key: `ANTHROPIC_API_KEY=sk-ant-...`
3. Restarted your application

### Permission Denied on Init

If you get EACCES errors, use the local installation:
```bash
npx @anthropic-ai/claude-code
```

Instead of the global installation.

### Import Errors in Python

Install dependencies:
```bash
cd backend
uv pip install -r requirements.txt
# or
pip install anthropic python-dotenv pydantic
```

## Integration with Existing Code

The Claude client follows the same pattern as your OpenAI and Gemini clients:

- Located at: `backend/claude_client.py`
- Same interface: `get_completion()`, `get_structured_completion()`, `analyze_image_with_vision()`
- Can be swapped in anywhere you use OpenAI or Gemini

Example:
```python
# Before (OpenAI)
from openai_client import openai_client
result = openai_client.get_completion(prompt)

# After (Claude)
from claude_client import claude_client
result = claude_client.get_completion(prompt)
```

## Next Steps

1. ✅ Install dependencies: `pip install -r backend/requirements.txt`
2. ✅ Set up `.env` file with your API key
3. ✅ Test the Python client
4. ✅ (Optional) Initialize Claude Code CLI
5. ✅ Start using Claude in your application!

## Resources

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude Code Documentation](https://docs.claude.com/claude-code)
- [Python SDK Reference](https://github.com/anthropics/anthropic-sdk-python)
- [Model Pricing](https://www.anthropic.com/pricing)

## Support

For issues or questions:
- Check the [Anthropic Discord](https://discord.gg/anthropic)
- Review [API Status](https://status.anthropic.com/)
- Contact support at support@anthropic.com

