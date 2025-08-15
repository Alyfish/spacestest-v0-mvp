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


class ImageUploadResponse(BaseModel):
    project_id: str
    image_path: str
    status: str
    message: str = "Image uploaded successfully"


class SpaceTypeRequest(BaseModel):
    space_type: str


class SpaceTypeResponse(BaseModel):
    project_id: str
    space_type: str
    status: str
    message: str = "Space type selected successfully"
