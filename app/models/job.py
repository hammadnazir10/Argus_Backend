from sqlalchemy import Column, String, DateTime, Integer, ARRAY, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List
from app.db.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    """Job PostgreSQL model - represents a bid analysis job."""
    
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(String(36), index=True, nullable=False)
    project_name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft", index=True)
    due_date = Column(DateTime, nullable=True)
    gc_name = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    bom_file_key = Column(String(500), nullable=True)
    quote_file_keys = Column(ARRAY(String), nullable=True, default=[])
    execution_arn = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<Job(id={self.id}, job_id={self.job_id}, user_id={self.user_id}, project_name={self.project_name}, client_name={self.client_name}, location={self.location})>"
