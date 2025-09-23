# Spaces AI Backend

AI-powered interior design recommendation system with product search and visualization.

## Environment Variables

Create a `.env` file in the backend directory with the following variables:

```bash
# OpenAI API for AI analysis and recommendations
OPENAI_API_KEY=your_openai_api_key_here

# SerpAPI for Google Shopping product search
SERP_API_KEY=your_serp_api_key_here

# OpenRouter API for AI image generation (accessing Gemini models)
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Run the development server:

```bash
uv run fastapi dev
```

The API will be available at `http://localhost:8000`

## API Features

- **Project Management**: Create and manage interior design projects
- **Image Analysis**: Upload room images and detect emptiness
- **Space Type Classification**: Identify room types (bedroom, living room, etc.)
- **Improvement Markers**: Place markers on images to identify improvement areas
- **AI Recommendations**: Generate design recommendations based on room analysis
- **Inspiration Analysis**: Upload inspiration images for style matching
- **Product Search**: Search for products using SerpAPI Google Shopping
- **Product Selection**: Select products for AI visualization
- **AI Design Analysis**: Generate professional interior design analysis using Gemini vision via OpenRouter

## Workflow

1. **Create Project** → Upload base room image
2. **Space Type Selection** → Classify the room type
3. **Marker Placement** → Mark areas for improvement
4. **AI Recommendations** → Get design suggestions
5. **Inspiration Upload** → Add inspiration images (optional)
6. **Product Recommendations** → Get product suggestions
7. **Product Search** → Search for specific products
8. **Product Selection** → Choose a product for design analysis
9. **AI Design Analysis** → Generate professional interior design analysis with OpenRouter

## API Documentation

FastAPI automatically generates documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
