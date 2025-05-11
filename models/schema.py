from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime

class ChatbotRequest(BaseModel):
    user_input: str

class ChatbotResponse(BaseModel):
    user_input: str
    response: str
    timestamp: datetime

    class Config:
        from_attributes = True  # Enables compatibility with SQLAlchemy models
        arbitrary_types_allowed = True

class UserSignupSchema(BaseModel):
    first_name: str # User's first name
    last_name: str # User's last name
    email: EmailStr # User's email address
    password: str # User's password

class UserResponseSchema(BaseModel):
    id: UUID4 # User's unique identifier
    first_name: str # User's first name
    last_name: str # User's last name
    email: EmailStr # User's email address
    is_active: bool # User's account status (active/inactive)
    is_superuser: bool = False # User's role (admin/non-admin)
    is_verified: bool # User's email verification status

class loginResponseSchema(BaseModel):
    success: bool # response status
    message: str # response message
    access_token: str # jwt session token
    token_type: str # the type of access token returned
    data: UserResponseSchema # user data
    
