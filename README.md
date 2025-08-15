# AI Interior Design Agent

An AI-powered interior design agent that helps users upgrade their living spaces through intelligent design recommendations and space optimization.

## Project Overview

This repository serves as a testing ground for an agentic backend architecture for an AI Interior Design Agent. The project consists of a FastAPI backend for the AI agent logic and a basic Next.js frontend for visualizing results.

## General Approach

### **Agentic Architecture Philosophy**

- **Project-Based Workflow**: Each user interaction starts a new project with a unique UUID
- **Context Accumulation**: Projects accumulate context through user inputs and AI responses
- **Iterative Development**: Features are built incrementally, testing agentic patterns as we go
- **Data-Driven Decisions**: Project context structure evolves based on actual usage patterns

### **Development Methodology**

- **Step-by-Step Implementation**: Each feature is built completely before moving to the next
- **Documentation-First**: All functionality is documented as it's implemented
- **Testing Focus**: Prioritize testing architectural patterns over production-ready features
- **Incremental Refinement**: Context structure and project flow are refined through iteration

### **Technical Approach**

- **JSON File Storage**: Simple, file-based storage for rapid prototyping and testing
- **React Query Integration**: Consistent data fetching patterns throughout the frontend
- **Type Safety**: Full TypeScript support for API contracts and data structures
- **URL-Based State**: Project state is managed through URL parameters for shareability

## Architecture

### Backend

- **Framework**: FastAPI
- **Package Manager**: uv
- **Purpose**: AI agent logic, design recommendations, space analysis
- **Location**: `/backend/`

### Frontend

- **Framework**: Next.js
- **Package Manager**: pnpm
- **UI Components**: shadcn/ui
- **Data Fetching**: React Query (TanStack Query)
- **Purpose**: Basic interface to visualize and interact with AI recommendations
- **Location**: `/frontend/`

## Project Structure

```
spaces_mvp/
├── backend/
│   ├── main.py          # FastAPI application entry point
│   ├── pyproject.toml   # Python project configuration
│   ├── uv.lock         # uv lock file
│   └── README.md       # Backend-specific documentation
├── frontend/
│   ├── src/
│   │   ├── app/        # Next.js app directory
│   │   └── lib/        # Utility functions
│   ├── package.json    # Node.js dependencies
│   ├── pnpm-lock.yaml  # pnpm lock file
│   └── components.json # shadcn/ui configuration
└── README.md           # This file
```

## Development Approach

- **Incremental Development**: Features will be added incrementally to test and refine the agentic architecture
- **Documentation**: All functionality will be documented as it's implemented
- **Step-by-Step Process**: Development follows a methodical, step-by-step approach
- **Testing Focus**: The repository prioritizes testing agentic backend patterns over production-ready features

## Frontend Guidelines

- **Data Fetching**: Use React Query (TanStack Query) exclusively for all API calls
- **UI Components**: Use Shadcn/ui components for consistent design and functionality
- **No Raw Fetch**: Avoid using raw fetch requests in components - always use React Query hooks
- **Type Safety**: Maintain full TypeScript support for all API interactions

## Backend Guidelines

- **Structured Output**: Use Pydantic models with `responses.parse` for type-safe AI responses
- **Model Selection**: Use GPT-5 constants (GPT_5, GPT_5_MINI, GPT_5_NANO) for consistency
- **Testing**: Use the CLI test script (`cli.py`) to validate structured output functionality

## Getting Started

### Backend Setup

```bash
cd backend
uv sync
uv run fastapi dev
```

### Testing Structured Output

```bash
cd backend
# Set your OpenAI API key
export OPENAI_API_KEY='your-api-key-here'

# Run the CLI test
uv run python cli.py
```

### Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

## Current Status

This is an active development repository for testing agentic AI backend architectures. The project is in early stages and will be updated incrementally as new features and architectural patterns are implemented.

## Features Implemented

- ✅ FastAPI backend with `/api` prefix for all routes
- ✅ React Query integration for data fetching
- ✅ Basic home screen with API endpoint testing
- ✅ CORS configuration for frontend-backend communication
- ✅ Project management system with JSON file storage
- ✅ Project creation and retrieval endpoints
- ✅ Dynamic project pages with URL-based routing
- ✅ Error handling for non-existent projects
- ✅ Image upload functionality with file storage
- ✅ Project status management (NEW → BASE_IMAGE_UPLOADED)
- ✅ Base image retrieval endpoint
- ✅ Image display on project pages
- ✅ OpenAI client with Pydantic-based structured responses (responses.parse)
- ✅ Returns validated Pydantic model instances
- ✅ GPT-5 model constants (GPT_5, GPT_5_MINI, GPT_5_NANO)
- ✅ CLI test script for structured output functionality

## Contributing

This is a personal project for testing and development purposes. All changes should be documented and follow the incremental development approach outlined above.
