from data_manager import data_manager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import ProjectCreateResponse, ProjectResponse

app = FastAPI(title="AI Interior Design Agent", version="1.0.0", root_path="/api")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "message": "AI Interior Design Agent is running"}


@app.get("/")
async def root():
    """Root API endpoint"""
    return {"message": "Welcome to AI Interior Design Agent API"}


@app.post("/projects", response_model=ProjectCreateResponse)
async def create_project():
    """Create a new project"""
    project_id = data_manager.create_project()
    project = data_manager.get_project(project_id)

    return ProjectCreateResponse(project_id=project_id, status=project["status"])


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a project by ID"""
    project = data_manager.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        project_id=project_id,
        status=project["status"],
        created_at=project["created_at"],
        context=project["context"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
