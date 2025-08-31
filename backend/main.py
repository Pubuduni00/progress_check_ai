
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import List
from datetime import datetime, timedelta
from bson import ObjectId

from config import Config
from database import (
    connect_to_mongo, close_mongo_connection, get_database, get_work_update_data,
    create_temp_work_update, get_temp_work_update, delete_temp_work_update,
    move_temp_to_permanent, cleanup_abandoned_temp_updates, get_database_stats
)
from ai_service import AIFollowupService
from models import (
    GenerateQuestionsRequest, GenerateQuestionsResponse, 
    FollowupAnswersUpdate, AnalysisResponse, TestAIResponse, 
    ErrorResponse, WorkUpdate, WorkUpdateCreate, FollowupSession, SessionStatus, WorkStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    try:
        Config.validate_config()
        await connect_to_mongo()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    await close_mongo_connection()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Intern Management AI Service",
    description="AI-powered follow-up question generation and analysis for intern management",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],  
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  
    allow_headers=["*"],
)

# Dependency to get AI service
async def get_ai_service() -> AIFollowupService:
    """Get AI service instance"""
    try:
        return AIFollowupService()
    except Exception as e:
        logger.error(f"Failed to initialize AI service: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI service initialization failed: {str(e)}"
        )

@app.get("/")
async def root():
    "Root endpoint"
    return {
        "message": "Intern Management AI Service",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db = get_database()
        # Test database connection
        await db.command("ping")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    try:
        stats = await get_database_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )

# STEP 1: Create work update CONDITIONALLY
@app.post("/api/work-updates")
async def create_work_update(work_update: WorkUpdateCreate):
    """Create work update - permanent for ON_LEAVE, temporary for WORKING"""
    try:
        # Validate work status and description
        if work_update.work_status == WorkStatus.WORKING:
            if not work_update.description or not work_update.description.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Work update description is required when status is 'working'"
                )
        
        db = get_database()
        today_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        if work_update.work_status == WorkStatus.ON_LEAVE:
            # ON LEAVE: Save directly to permanent collection
            work_updates_collection = db[Config.WORK_UPDATES_COLLECTION]
            date_based_query = {"userId": work_update.userId, "update_date": today_date}
            existing_update = await work_updates_collection.find_one(date_based_query)

            update_dict = work_update.dict(exclude={"id"})
            update_dict["update_date"] = today_date
            update_dict["submittedAt"] = datetime.utcnow()
            update_dict["followupCompleted"] = True  # No follow-up needed for leave
            update_dict["status"] = "completed"  

            if existing_update:
                await work_updates_collection.replace_one({"_id": existing_update["_id"]}, update_dict)
                work_update_id = str(existing_update["_id"])
                is_override = True
            else:
                result = await work_updates_collection.insert_one(update_dict)
                work_update_id = str(result.inserted_id)
                is_override = False

            logger.info(f"ON LEAVE work update saved permanently: {work_update_id}")
            
            return {
                "message": "Leave status saved successfully",
                "workUpdateId": work_update_id,
                "isOverride": is_override,
                "redirectToFollowup": False,
                "isOnLeave": True
            }
        
        else:
            # WORKING: Save to TEMPORARY collection (pending follow-up)
            update_dict = work_update.dict(exclude={"id"})
            update_dict["update_date"] = today_date
            update_dict["submittedAt"] = datetime.utcnow()
            update_dict["status"] = "pending_followup"  
            update_dict["followupCompleted"] = False

            # Use database function to create temp work update
            temp_work_update_id = await create_temp_work_update(update_dict)
            
            logger.info(f"WORKING work update saved to temp collection: {temp_work_update_id}")
            
            return {
                "message": "Work update saved temporarily. Complete follow-up to finalize.",
                "tempWorkUpdateId": temp_work_update_id,  
                "redirectToFollowup": True,
                "isOnLeave": False
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating work update: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create work update: {str(e)}"
        )

#  Start follow-up session using TEMP work update
@app.post("/api/followups/start")
async def start_followup_session(
    temp_work_update_id: str, 
    user_id: str,
    ai_service: AIFollowupService = Depends(get_ai_service)
):
    """Start follow-up session using temporary work update data"""
    try:
        db = get_database()
        followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]

        # Get TEMPORARY work update data using database function
        temp_work_update = await get_temp_work_update(temp_work_update_id)
        if not temp_work_update:
            raise HTTPException(status_code=404, detail="Temporary work update not found")

        today_date = datetime.utcnow().strftime('%Y-%m-%d')
        session_date_id = f"{user_id}_session_{today_date}"

        # Generate questions using temp data
        ai_input_data = {
            "description": temp_work_update.get("description"),
            "challenges": temp_work_update.get("challenges"),
            "plans": temp_work_update.get("plans"),
            "user_id": user_id
        }
        questions = await ai_service.generate_followup_questions(user_id, work_update_data=ai_input_data)


        session_doc = {
            "_id": session_date_id,
            "userId": user_id,
            "tempWorkUpdateId": temp_work_update_id, 
            "session_date": today_date,
            "questions": questions,
            "answers": [""] * len(questions),
            "status": SessionStatus.PENDING,
            "createdAt": datetime.utcnow(),
            "completedAt": None
        }
        await followup_collection.replace_one({"_id": session_date_id}, session_doc, upsert=True)

        logger.info(f"Follow-up session started with temp work update: {temp_work_update_id}")

        return {
            "message": "Follow-up session started",
            "sessionId": session_date_id,
            "questions": questions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting follow-up session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start follow-up session: {str(e)}"
        )

#  Complete follow-up and MOVE temp to permanent
@app.put("/api/followup/{session_id}/complete")
async def complete_followup_session(
    session_id: str,
    answers_update: FollowupAnswersUpdate
):
    """Complete follow-up session and move temp work update to permanent collection"""
    try:
        # Validate all answers provided
        if not answers_update.answers or len(answers_update.answers) != 3:
            raise HTTPException(
                status_code=400,
                detail="All 3 questions must be answered"
            )
        
        # Check if any answer is empty
        if any(not answer.strip() for answer in answers_update.answers):
            raise HTTPException(
                status_code=400,
                detail="All questions must have non-empty answers"
            )
        
        db = get_database()
        followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]
        
        # Get the follow-up session
        session = await followup_collection.find_one({"_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get the temporary work update using database function
        temp_work_update = await get_temp_work_update(session["tempWorkUpdateId"])
        if not temp_work_update:
            raise HTTPException(status_code=404, detail="Temporary work update not found")

        # Complete the follow-up session
        session_update = {
            "answers": answers_update.answers,
            "status": SessionStatus.COMPLETED,
            "completedAt": datetime.utcnow()
        }
        
        await followup_collection.update_one(
            {"_id": session_id},
            {"$set": session_update}
        )

        # MOVE temp work update to permanent collection using database function
        final_work_update_id = await move_temp_to_permanent(
            session["tempWorkUpdateId"],
            {"completedAt": datetime.utcnow()}
        )

        # Update session with permanent work update ID
        await followup_collection.update_one(
            {"_id": session_id},
            {"$set": {"workUpdateId": final_work_update_id}}
        )

        logger.info(f"Follow-up session {session_id} completed and work update finalized: {final_work_update_id}")
        
        return {
            "message": "Follow-up questions completed successfully. Work update finalized.",
            "sessionId": session_id,
            "workUpdateId": final_work_update_id,
            "workUpdateCompleted": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete follow-up: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete follow-up: {str(e)}"
        )

# Cleanup endpoint for temporary work updates
@app.delete("/api/temp-work-updates/cleanup")
async def cleanup_abandoned_temp_updates_endpoint():
    """Clean up temporary work updates older than 24 hours"""
    try:
        deleted_count = await cleanup_abandoned_temp_updates(24)
        
        return {
            "message": f"Cleaned up {deleted_count} abandoned temporary work updates",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup: {str(e)}"
        )

# Get specific follow-up session
@app.get("/api/followup/session/{session_id}")
async def get_followup_session(session_id: str):
    """Get specific follow-up session details"""
    try:
        db = get_database()
        followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]
        
        session = await followup_collection.find_one({"_id": session_id})
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Convert ObjectId to string for JSON serialization
        session["sessionId"] = session["_id"]
        if "_id" in session:
            del session["_id"]
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session: {str(e)}"
        )


@app.get("/api/followup-sessions/{user_id}")
async def get_followup_sessions(
    user_id: str,
    limit: int = 150,
    skip: int = 0
):
    """Get follow-up sessions for a user"""
    try:
        db = get_database()
        followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]
        
        cursor = followup_collection.find(
            {"userId": user_id}
        ).sort("createdAt", -1).skip(skip).limit(limit)
        
        sessions = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for session in sessions:
            if "_id" in session:
                session["id"] = str(session["_id"])
                session["sessionId"] = session["_id"]
                del session["_id"]
        
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error getting followup sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get followup sessions: {str(e)}"
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return {
        "error": "HTTP_ERROR",
        "message": exc.detail,
        "status_code": exc.status_code
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "INTERNAL_ERROR", 
        "message": "An internal error occurred",
        "details": str(exc) if Config.DEBUG else None
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=Config.DEBUG,
        log_level="info"
    )