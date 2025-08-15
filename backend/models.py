from pydantic import BaseModel


class ProjectCreateResponse(BaseModel):
    project_id: str
    status: str
    message: str = "Project created successfully"


class ProjectResponse(BaseModel):
    project_id: str
    status: str
    created_at: str
    context: dict


class ErrorResponse(BaseModel):
    error: str
    message: str
