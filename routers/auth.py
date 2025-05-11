import os
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from config.database import get_session
from dependencies.error import httpError
from dependencies.auth import (
    check_userSignupSchema,
    create_access_token,
    hash_password,
    verify_password,
)
from models.models import User
from models.schema import UserResponseSchema, UserSignupSchema, loginResponseSchema

router = APIRouter()

# Configuration for JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # Replace with a secure secret key
ALGORITHM = "HS256"
token_expiration = int(os.getenv("JWT_TOKEN_EXPIRY_MINUTES", 24 * 60))

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_session),
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("userId")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Fetch the user from the database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/auth/signup", status_code=201)
async def user_signup(userSchema: UserSignupSchema, db: Session = Depends(get_session)):
    """Endpoint for user registration"""
    try:
        userDict: dict[str, str] = userSchema.model_dump()
        check_userSignupSchema(userDict, db)
        userDict["password"] = hash_password(userDict["password"])
        user = User(**userDict)
        user.save(db)
        newUser: User = db.query(User).filter(User.email == userDict["email"]).first()  # type: ignore
        newUserDict: dict[str, str | bool] = newUser.__dict__
        del newUserDict["password"]
        return {
            "success": True,
            "message": "User created successfully.",
            "data": newUserDict,
        }
    except Exception as e:
        print(str(e))
        if isinstance(e, HTTPException):
            raise e
        raise httpError(status_code=500, detail=str(e))


@router.post("/auth/login", status_code=200, response_model=loginResponseSchema)
async def user_login(
    userSchema: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_session),
):
    """Endpoint for user login"""
    try:
        user = db.query(User).filter(User.email == userSchema.username).first()
        if not user:
            raise httpError(status_code=404, detail="User with email provided not found")
        if not verify_password(userSchema.password, hashed=str(user.password)):
            raise httpError(status_code=401, detail="Invalid password")
        token = create_access_token(
            {"userEmail": userSchema.username, "userId": user.id},  # The user email will be passed as the username because the Oauth class only allows us to use the username and password parameters
            expires_delta=timedelta(minutes=token_expiration),
        )
        if not token:
            raise Exception("Error creating jwt")
        loggedInUser: dict[str, str | bool] = user.__dict__
        del loggedInUser["password"]
        return {
            "success": True,
            "message": "User logged in successfully.",
            "access_token": token,
            "token_type": "bearer",
            "data": loggedInUser,
        }
    except Exception as e:
        print(str(e))
        if isinstance(e, HTTPException):
            raise e
        raise httpError(status_code=500, detail=str(e))


@router.get("/auth/user/me", status_code=200, response_model=UserResponseSchema)
async def get_user(
    current_user: User = Depends(get_current_user),
):
    """Endpoint for getting user details"""
    try:
        return {
            "id": current_user.id,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "is_verified": current_user.is_verified,
        }
    except HTTPException as e:
        print(str(e))
        raise e
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))