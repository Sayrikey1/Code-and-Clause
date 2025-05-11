from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    String,
    ForeignKey,
    Enum
)

from enum import Enum as PyEnum

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from config.database import SessionLocal

Base = declarative_base()

class Basemodel:
    """Basemodel for other database tables to inherit"""

    id = Column(String(60), index=True, primary_key=True, default=lambda: str(uuid4()))  # object's unique id
    created_at = Column(DateTime, default=datetime.now(timezone.utc))  # object's creation date
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))  # object's update date

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key != '__class__':
                setattr(self, key, value)
    
    def save(self, session: SessionLocal): # type: ignore
        """Save object to database"""
        self.updated_at = datetime.now(timezone.utc)
        session.add(self)
        session.commit()
    
    def to_dict(self):
        """Returns a dictionary containing all keys/values of the instance"""
        new_dict = self.__dict__.copy()
        if "__class__" in new_dict:
            del new_dict["__class__"] 
        return new_dict

class UserRole(PyEnum):
    STAFF = "staff"
    ADMIN = "admin"

class User(Basemodel, Base):
    __tablename__ = "users"

    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STAFF, nullable=False)
    phone = Column(String(15), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender = Column(String(10), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    chatbot_interactions = relationship("ChatbotInteraction", back_populates="user", cascade="all, delete-orphan")

class ChatbotInteraction(Basemodel, Base):
    __tablename__ = "chatbot_interactions"

    user_id = Column(String(60), ForeignKey("users.id"), nullable=False)
    user_input = Column(String(15000), nullable=False)  # User's question
    response = Column(String(15000), nullable=False)  # Chatbot's reply
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="chatbot_interactions")
