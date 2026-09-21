from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    module: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AssignPermissionsRequest(BaseModel):
    permission_codes: List[str]


class AssignRoleRequest(BaseModel):
    user_public_id: str
    role_id: int


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_system_role: bool = False
    tenant_id: Optional[int] = None
    permissions: List[PermissionResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
