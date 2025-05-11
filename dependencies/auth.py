#!/usr/bin/env python

import os
from datetime import datetime, timedelta

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .error import httpError
from models.models import User

load_dotenv()

secret_key = os.getenv("JWT_SECRET_KEY")
algorithm = os.getenv("JWT_ALGORITHM")


def check_userSignupSchema(user: dict, db: Session):
    """
    Checks if all required fields are provided for user registration
    and confirms if the user exists
    """
    if user.get("email") is None or len(user.get("email")) == 0: # type: ignore
        # Checks if email address is provided
        raise httpError(status_code=400, detail="Email address is required")
    elif user.get("first_name") is None or len(user.get("first_name")) == 0: # type: ignore
        # Checks if first name is provided
        raise httpError(status_code=400, detail="First name is required")
    elif user.get("last_name") is None or len(user.get("last_name")) == 0: # type: ignore
        # Checks if last name is provided
        raise httpError(status_code=400, detail="Last name is required")
    elif user.get("password") is None or len(user.get("password")) == 0: # type: ignore
        # Checks if password is provided
        raise httpError(status_code=400, detail="Business name is required")
    elif db.query(User).filter(User.email == user.get("email")).first() is not None: # type: ignore
        # Checks if user already exists with supplied email address
        raise httpError(status_code=400, detail="User already exists")

def hash_password(password: str):
    """
    Hashes user's password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta):
    """
    Creates a jwt token for user login session
    """
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm)
    return encoded_jwt

def validate_user(token: str):
    """
    Validates a user's jwt token to identify the user
    """
    credentials_exception = httpError(status_code=401, detail="Request not authorized")
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        email: str = str(payload.get("userEmail"))
        id: str = str(payload.get("userId"))
        if email is None:
            print("No email")
            raise credentials_exception
        if id is None:
            print("No user id")
            raise credentials_exception
        return id
    except JWTError as e:
        print("jwt err: {}".format(str(e)))
        raise credentials_exception

def verify_password(password: str, hashed: str):
    """
    Verifies user's password
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
