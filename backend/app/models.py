from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class ApiErrorResponse(BaseModel):
    code: str
    message: str

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3,max_length=20)
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=5,max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CheckResult(BaseModel):
    status: str  # pass, warn, fail
    summary: str
    details: list[str] = []


class UploadResponse(BaseModel):
    deployment_id: str
    name: str
    file_count: int
    total_size: int
    security: CheckResult
    cost: CheckResult
    brand: CheckResult


class DeployRequest(BaseModel):
    mode: str = "demo"  # demo or prod


class DeployResponse(BaseModel):
    deployment_id: str
    cloud_run_url: str
    mode: str
    expires_at: Optional[str] = None


class Deployment(BaseModel):
    id: str
    name: str
    status: str
    mode: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    security_status: Optional[str] = None
    security_details: Optional[str] = None
    cost_status: Optional[str] = None
    cost_details: Optional[str] = None
    brand_status: Optional[str] = None
    brand_details: Optional[str] = None
    cloud_run_url: Optional[str] = None
    created_at: str
    deployed_at: Optional[str] = None
    expires_at: Optional[str] = None
