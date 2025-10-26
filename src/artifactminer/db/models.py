from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from .database import Base

class Artifact(Base):#basic model for artifacts, this will be used to store artifact information in the database
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)#unique identifier for each artifact
    name = Column(String)#name of the artifact
    path = Column(String, unique=True)#file system path to the artifact
    type = Column(String)#type of the artifact like file or directory
    scanned_at = Column(DateTime, default=datetime.utcnow) #timestamp when the artifact was scanned

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String, nullable=False)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    accepted = Column(Boolean, default=False, nullable=False)
    version = Column(String, default="v0", nullable=False)
    accepted_at = Column(DateTime, nullable=True)
