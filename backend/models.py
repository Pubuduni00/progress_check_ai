
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"

class WorkStatus(str, Enum):
    WORKING = "working"
    ON_LEAVE = "on_leave"

class WorkUpdateCreate(BaseModel):
    userId: str
    # Add work status field (radio button: working/on_leave)
    work_status: WorkStatus = WorkStatus.WORKING  # Default to working
    description: Optional[str] = None  
    challenges: Optional[str] = None  # Challenges for today (optional)
    plans: Optional[str] = None  # Plans for tomorrow (optional)
    submittedAt: Optional[datetime] = Field(default_factory=datetime.utcnow)
    # Date-based tracking for same-day override
    update_date: Optional[str] = Field(default=None)  

class WorkUpdate(WorkUpdateCreate):
    id: Optional[str] = Field(default=None, alias="_id")   
    followupCompleted: Optional[bool] = Field(default=False)  # Track followup completion
    # Add date-based session tracking
    session_date_id: Optional[str] = Field(default=None)  # Store date-based session ID
    # Track if followup was skipped due to leave
    followup_skipped: Optional[bool] = Field(default=False)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

class FollowupSessionCreate(BaseModel):
    userId: str
    workUpdateId: Optional[str] = None  
    questions: List[str]
    answers: Optional[List[str]] = Field(default_factory=list)
    status: SessionStatus = SessionStatus.PENDING
    createdAt: Optional[datetime] = Field(default_factory=datetime.utcnow)
    completedAt: Optional[datetime] = None
    # Add date tracking for sessions
    session_date: Optional[str] = Field(default=None) 

class FollowupSession(FollowupSessionCreate):
    id: Optional[str] = Field(alias="_id")             
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

class FollowupAnswersUpdate(BaseModel):
    answers: List[str]

class GenerateQuestionsRequest(BaseModel):
    userId: str

class GenerateQuestionsResponse(BaseModel):
    questions: List[str]
    sessionId: str

class AnalysisResponse(BaseModel):
    analysis: str

class TestAIResponse(BaseModel):
    success: bool
    message: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Any] = None