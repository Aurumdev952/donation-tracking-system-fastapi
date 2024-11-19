from datetime import datetime
from typing import List, Optional

from fastapi import Form, UploadFile
from pydantic import BaseModel, EmailStr
from sqlmodel import Field, Relationship, SQLModel


class UserBase(SQLModel):
    username: str
    email: EmailStr
    password: str


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    donations: List["Donation"] = Relationship(back_populates="donor")


class CauseBase(SQLModel):
    name: str
    tagline: str
    description: str
    end_date: datetime
    banner_image: Optional[str] = None
    cover_image: Optional[str] = None


class Cause(CauseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    donations: List["Donation"] = Relationship(back_populates="cause")


class DonationBase(SQLModel):
    amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Donation(DonationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    donor_id: int = Field(foreign_key="user.id")
    cause_id: int = Field(foreign_key="cause.id")
    donor: Optional[User] = Relationship(back_populates="donations")
    cause: Optional[Cause] = Relationship(back_populates="donations")


# Request Schemas for CRUD Operations
class UserCreate(UserBase):
    pass


class CauseCreate(CauseBase):
    pass


class DonationCreate(DonationBase):
    pass


class CauseUpdate(CauseBase):
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[datetime] = None
    banner_image: Optional[str] = None
    cover_image: Optional[str] = None


class CauseForm(BaseModel):
    name: str
    tagline: str
    description: str
    end_date: str  # ISO 8601 formatted date-time
    banner_image: UploadFile
    cover_image: UploadFile

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        tagline: str = Form(...),
        description: str = Form(...),
        end_date: str = Form(...),
        banner_image: UploadFile = Form(...),
        cover_image: UploadFile = Form(...),
    ):
        """
        Use this class method to enable dependency injection for form fields.
        """
        return cls(
            name=name,
            tagline=tagline,
            description=description,
            end_date=end_date,
            banner_image=banner_image,
            cover_image=cover_image,
        )
