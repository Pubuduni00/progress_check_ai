
# from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
# from fastapi.middleware.cors import CORSMiddleware
# from contextlib import asynccontextmanager
# import logging
# from typing import List
# from datetime import datetime, timedelta
# from bson import ObjectId
# import asyncio

# from config import Config
# from database import (
#     connect_to_mongo, close_mongo_connection, get_database, get_work_update_data,
#     create_temp_work_update, get_temp_work_update, delete_temp_work_update,
#     move_temp_to_permanent, cleanup_abandoned_temp_updates, get_database_stats
# )
# from ai_service import AIFollowupService
# from models import (
#     GenerateQuestionsRequest, GenerateQuestionsResponse, 
#     FollowupAnswersUpdate, AnalysisResponse, TestAIResponse, 
#     ErrorResponse, WorkUpdate, WorkUpdateCreate, FollowupSession, SessionStatus, WorkStatus
# )

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# # Global variable to control the cleanup task
# cleanup_task = None

# async def scheduled_cleanup_task():
#     """Background task that runs cleanup every hour"""
#     while True:
#         try:
#             logger.info("Running scheduled cleanup of abandoned temp updates...")
#             result = await cleanup_abandoned_temp_updates(24)  # Clean up items older than 24 hours
            
#             deleted_temp = result.get("deleted_temp_updates", 0)
#             deleted_sessions = result.get("deleted_sessions", 0)
            
#             if deleted_temp > 0 or deleted_sessions > 0:
#                 logger.info(f"Scheduled cleanup: Removed {deleted_temp} temp updates and {deleted_sessions} sessions")
#             else:
#                 logger.info("Scheduled cleanup: No abandoned items found")
                
#         except Exception as e:
#             logger.error(f"Error in scheduled cleanup: {e}")
        
#         # Wait for 1 hour before next cleanup
#         await asyncio.sleep(3600)  # 3600 seconds = 1 hour

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Application lifespan manager"""
#     global cleanup_task
    
#     # Startup
#     try:
#         Config.validate_config()
#         await connect_to_mongo()
        
#         # Start the background cleanup task
#         cleanup_task = asyncio.create_task(scheduled_cleanup_task())
#         logger.info("Background cleanup task started")
        
#         logger.info("Application started successfully")
#     except Exception as e:
#         logger.error(f"Failed to start application: {e}")
#         raise
    
#     yield
    
#     # Shutdown
#     if cleanup_task:
#         cleanup_task.cancel()
#         try:
#             await cleanup_task
#         except asyncio.CancelledError:
#             logger.info("Background cleanup task cancelled")
    
#     await close_mongo_connection()
#     logger.info("Application shutdown complete")

# # Create FastAPI app
# app = FastAPI(
#     title="Intern Management AI Service",
#     description="AI-powered follow-up question generation and analysis for intern management",
#     version="1.0.0",
#     lifespan=lifespan
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],  
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE"],  
#     allow_headers=["*"],
# )

# # Dependency to get AI service
# async def get_ai_service() -> AIFollowupService:
#     """Get AI service instance"""
#     try:
#         return AIFollowupService()
#     except Exception as e:
#         logger.error(f"Failed to initialize AI service: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"AI service initialization failed: {str(e)}"
#         )

# @app.get("/")
# async def root():
#     "Root endpoint"
#     return {
#         "message": "Intern Management AI Service",
#         "version": "1.0.0",
#         "status": "running",
#         "cleanup_task_status": "running" if cleanup_task and not cleanup_task.done() else "stopped"
#     }

# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     try:
#         db = get_database()
#         # Test database connection
#         await db.command("ping")
        
#         return {
#             "status": "healthy",
#             "database": "connected",
#             "cleanup_task_running": cleanup_task and not cleanup_task.done(),
#             "timestamp": datetime.now().isoformat()
#         }
#     except Exception as e:
#         logger.error(f"Health check failed: {e}")
#         return {
#             "status": "unhealthy",
#             "error": str(e),
#             "cleanup_task_running": False,
#             "timestamp": datetime.now().isoformat()
#         }

# @app.get("/stats")
# async def get_stats():
#     """Get database statistics"""
#     try:
#         stats = await get_database_stats()
#         # Add cleanup task status to stats
#         stats["cleanup_task"] = {
#             "running": cleanup_task and not cleanup_task.done(),
#             "next_cleanup": "every hour"
#         }
#         return stats
#     except Exception as e:
#         logger.error(f"Failed to get stats: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to get statistics: {str(e)}"
#         )

# # New endpoint to check cleanup task status
# @app.get("/api/cleanup/status")
# async def get_cleanup_status():
#     """Get status of the background cleanup task"""
#     return {
#         "cleanup_task_running": cleanup_task and not cleanup_task.done(),
#         "cleanup_frequency": "Every 1 hour",
#         "cleanup_age_threshold": "24 hours",
#         "last_run_info": "Check logs for detailed cleanup results"
#     }

# # STEP 1: Create work update CONDITIONALLY
# @app.post("/api/work-updates")
# async def create_work_update(work_update: WorkUpdateCreate):
#     """Create work update - permanent for ON_LEAVE, temporary for WORKING"""
#     try:
#         # Validate work status and description
#         if work_update.work_status == WorkStatus.WORKING:
#             if not work_update.description or not work_update.description.strip():
#                 raise HTTPException(
#                     status_code=400,
#                     detail="Work update description is required when status is 'working'"
#                 )
        
#         db = get_database()
#         today_date = datetime.now().strftime('%Y-%m-%d')
        
#         if work_update.work_status == WorkStatus.ON_LEAVE:
#             # ON LEAVE: Save directly to permanent collection
#             work_updates_collection = db[Config.WORK_UPDATES_COLLECTION]
#             date_based_query = {"userId": work_update.userId, "update_date": today_date}
#             existing_update = await work_updates_collection.find_one(date_based_query)

#             update_dict = work_update.dict(exclude={"id"})
#             update_dict["update_date"] = today_date
#             update_dict["submittedAt"] = datetime.now()
#             update_dict["followupCompleted"] = True  # No follow-up needed for leave
#             update_dict["status"] = "completed"  

#             if existing_update:
#                 await work_updates_collection.replace_one({"_id": existing_update["_id"]}, update_dict)
#                 work_update_id = str(existing_update["_id"])
#                 is_override = True
#             else:
#                 result = await work_updates_collection.insert_one(update_dict)
#                 work_update_id = str(result.inserted_id)
#                 is_override = False

#             logger.info(f"ON LEAVE work update saved permanently: {work_update_id}")
            
#             return {
#                 "message": "Leave status saved successfully",
#                 "workUpdateId": work_update_id,
#                 "isOverride": is_override,
#                 "redirectToFollowup": False,
#                 "isOnLeave": True
#             }
        
#         else:
#             # WORKING: Save to TEMPORARY collection (pending follow-up)
#             update_dict = work_update.dict(exclude={"id"})
#             update_dict["update_date"] = today_date
#             update_dict["submittedAt"] = datetime.now()
#             update_dict["status"] = "pending_followup"  
#             update_dict["followupCompleted"] = False

#             # Use database function to create temp work update
#             temp_work_update_id = await create_temp_work_update(update_dict)
            
#             logger.info(f"WORKING work update saved to temp collection: {temp_work_update_id}")
            
#             return {
#                 "message": "Work update saved temporarily. Complete follow-up to finalize.",
#                 "tempWorkUpdateId": temp_work_update_id,  
#                 "redirectToFollowup": True,
#                 "isOnLeave": False
#             }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error creating work update: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to create work update: {str(e)}"
#         )

# #  Start follow-up session using TEMP work update
# @app.post("/api/followups/start")
# async def start_followup_session(
#     temp_work_update_id: str, 
#     user_id: str,
#     ai_service: AIFollowupService = Depends(get_ai_service)
# ):
#     """Start follow-up session using temporary work update data"""
#     try:
#         db = get_database()
#         followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]

#         # Get TEMPORARY work update data using database function
#         temp_work_update = await get_temp_work_update(temp_work_update_id)
#         if not temp_work_update:
#             raise HTTPException(status_code=404, detail="Temporary work update not found")

#         today_date = datetime.now().strftime('%Y-%m-%d')
#         session_date_id = f"{user_id}_session_{today_date}"

#         # Generate questions using temp data
#         ai_input_data = {
#             "description": temp_work_update.get("description"),
#             "challenges": temp_work_update.get("challenges"),
#             "plans": temp_work_update.get("plans"),
#             "user_id": user_id
#         }
#         questions = await ai_service.generate_followup_questions(user_id, work_update_data=ai_input_data)

#         session_doc = {
#             "_id": session_date_id,
#             "userId": user_id,
#             "tempWorkUpdateId": temp_work_update_id, 
#             "session_date": today_date,
#             "questions": questions,
#             "answers": [""] * len(questions),
#             "status": SessionStatus.PENDING,
#             "createdAt": datetime.now(),
#             "completedAt": None
#         }
#         await followup_collection.replace_one({"_id": session_date_id}, session_doc, upsert=True)

#         logger.info(f"Follow-up session started with temp work update: {temp_work_update_id}")

#         return {
#             "message": "Follow-up session started",
#             "sessionId": session_date_id,
#             "questions": questions
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error starting follow-up session: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to start follow-up session: {str(e)}"
#         )

# #  Complete follow-up and MOVE temp to permanent
# @app.put("/api/followup/{session_id}/complete")
# async def complete_followup_session(
#     session_id: str,
#     answers_update: FollowupAnswersUpdate
# ):
#     """Complete follow-up session and move temp work update to permanent collection"""
#     try:
#         # Validate all answers provided
#         if not answers_update.answers or len(answers_update.answers) != 3:
#             raise HTTPException(
#                 status_code=400,
#                 detail="All 3 questions must be answered"
#             )
        
#         # Check if any answer is empty
#         if any(not answer.strip() for answer in answers_update.answers):
#             raise HTTPException(
#                 status_code=400,
#                 detail="All questions must have non-empty answers"
#             )
        
#         db = get_database()
#         followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]
        
#         # Get the follow-up session
#         session = await followup_collection.find_one({"_id": session_id})
#         if not session:
#             raise HTTPException(status_code=404, detail="Session not found")

#         # Get the temporary work update using database function
#         temp_work_update = await get_temp_work_update(session["tempWorkUpdateId"])
#         if not temp_work_update:
#             raise HTTPException(status_code=404, detail="Temporary work update not found")

#         # Complete the follow-up session
#         session_update = {
#             "answers": answers_update.answers,
#             "status": SessionStatus.COMPLETED,
#             "completedAt": datetime.now()
#         }
        
#         await followup_collection.update_one(
#             {"_id": session_id},
#             {"$set": session_update}
#         )

#         # MOVE temp work update to permanent collection using database function
#         final_work_update_id = await move_temp_to_permanent(
#             session["tempWorkUpdateId"],
#             {"completedAt": datetime.now()}
#         )

#         # Update session with permanent work update ID
#         await followup_collection.update_one(
#             {"_id": session_id},
#             {"$set": {"workUpdateId": final_work_update_id}}
#         )

#         logger.info(f"Follow-up session {session_id} completed and work update finalized: {final_work_update_id}")
        
#         return {
#             "message": "Follow-up questions completed successfully. Work update finalized.",
#             "sessionId": session_id,
#             "workUpdateId": final_work_update_id,
#             "workUpdateCompleted": True
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Failed to complete follow-up: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to complete follow-up: {str(e)}"
#         )

# # Manual cleanup endpoint (now also available alongside automatic cleanup)
# @app.delete("/api/temp-work-updates/cleanup")
# async def cleanup_abandoned_temp_updates_endpoint():
#     """Manually trigger cleanup of temporary work updates older than 24 hours"""
#     try:
#         result = await cleanup_abandoned_temp_updates(24)
#         deleted_temp = result.get("deleted_temp_updates", 0)
#         deleted_sessions = result.get("deleted_sessions", 0)
        
#         return {
#             "message": f"Manual cleanup completed. Cleaned up {deleted_temp} temp updates and {deleted_sessions} sessions",
#             "deleted_temp_updates": deleted_temp,
#             "deleted_sessions": deleted_sessions,
#             "note": "Automatic cleanup runs every hour in the background"
#         }
        
#     except Exception as e:
#         logger.error(f"Error during manual cleanup: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to cleanup: {str(e)}"
#         )

# # Get specific follow-up session
# @app.get("/api/followup/session/{session_id}")
# async def get_followup_session(session_id: str):
#     """Get specific follow-up session details"""
#     try:
#         db = get_database()
#         followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]
        
#         session = await followup_collection.find_one({"_id": session_id})
        
#         if not session:
#             raise HTTPException(status_code=404, detail="Session not found")
        
#         # Convert ObjectId to string for JSON serialization
#         session["sessionId"] = session["_id"]
#         if "_id" in session:
#             del session["_id"]
        
#         return session
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Failed to get session: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to get session: {str(e)}"
#         )

# @app.get("/api/followup-sessions/{user_id}")
# async def get_followup_sessions(
#     user_id: str,
#     limit: int = 150,
#     skip: int = 0
# ):
#     """Get follow-up sessions for a user"""
#     try:
#         db = get_database()
#         followup_collection = db[Config.FOLLOWUP_SESSIONS_COLLECTION]
        
#         cursor = followup_collection.find(
#             {"userId": user_id}
#         ).sort("createdAt", -1).skip(skip).limit(limit)
        
#         sessions = await cursor.to_list(length=limit)
        
#         # Convert ObjectId to string for JSON serialization
#         for session in sessions:
#             if "_id" in session:
#                 session["id"] = str(session["_id"])
#                 session["sessionId"] = session["_id"]
#                 del session["_id"]
        
#         return {
#             "sessions": sessions,
#             "count": len(sessions)
#         }
        
#     except Exception as e:
#         logger.error(f"Error getting followup sessions: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to get followup sessions: {str(e)}"
#         )

# # Error handlers
# @app.exception_handler(HTTPException)
# async def http_exception_handler(request, exc: HTTPException):
#     """Handle HTTP exceptions"""
#     return {
#         "error": "HTTP_ERROR",
#         "message": exc.detail,
#         "status_code": exc.status_code
#     }

# @app.exception_handler(Exception)
# async def general_exception_handler(request, exc: Exception):
#     """Handle general exceptions"""
#     logger.error(f"Unhandled exception: {exc}")
#     return {
#         "error": "INTERNAL_ERROR", 
#         "message": "An internal error occurred",
#         "details": str(exc) if Config.DEBUG else None
#     }

# if __name__ == "__main__":
#     import uvicorn
    
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=Config.DEBUG,
#         log_level="info"
#     )


from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import List
from datetime import datetime, timedelta
from bson import ObjectId
import asyncio

from config import Config
from database import (
    connect_to_mongo, close_mongo_connection, get_database, get_work_update_data,
    create_temp_work_update, get_temp_work_update, delete_temp_work_update,
    move_temp_to_permanent, cleanup_abandoned_temp_updates, get_database_stats,
    verify_ttl_index  # Import TTL verification function
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

# Global variable to control the cleanup task
cleanup_task = None

async def scheduled_cleanup_task():
    """Background task that runs cleanup every hour (backup to TTL)"""
    while True:
        try:
            logger.info("Running scheduled manual cleanup (backup to TTL)...")
            
            # Verify TTL is working
            ttl_working = await verify_ttl_index()
            
            if ttl_working:
                logger.info("TTL index is active - automatic deletion is working")
                # Still run manual cleanup as backup, but less frequent
                result = await cleanup_abandoned_temp_updates(25)  # Clean slightly older items as backup
            else:
                logger.warning("TTL index not found! Running manual cleanup more aggressively")
                result = await cleanup_abandoned_temp_updates(24)  # Regular cleanup
            
            deleted_temp = result.get("deleted_temp_updates", 0)
            deleted_sessions = result.get("deleted_sessions", 0)
            
            if deleted_temp > 0 or deleted_sessions > 0:
                cleanup_type = "backup" if ttl_working else "primary"
                logger.info(f"Scheduled {cleanup_type} cleanup: Removed {deleted_temp} temp updates and {deleted_sessions} sessions")
            else:
                status = "TTL working properly" if ttl_working else "No items found"
                logger.info(f"Scheduled cleanup: {status}")
                
        except Exception as e:
            logger.error(f"Error in scheduled cleanup: {e}")
        
        # Wait for 1 hour before next cleanup
        await asyncio.sleep(3600)  # 3600 seconds = 1 hour

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global cleanup_task
    
    # Startup
    try:
        Config.validate_config()
        await connect_to_mongo()
        
        # Verify TTL index is working
        ttl_status = await verify_ttl_index()
        if ttl_status:
            logger.info("✅ TTL index verified - automatic cleanup is active")
        else:
            logger.warning("⚠️ TTL index not found - relying on manual cleanup")
        
        # Start the background cleanup task (as backup to TTL)
        cleanup_task = asyncio.create_task(scheduled_cleanup_task())
        logger.info("Background cleanup task started (backup to TTL)")
        
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("Background cleanup task cancelled")
    
    await close_mongo_connection()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Intern Management AI Service",
    description="AI-powered follow-up question generation and analysis for intern management with automatic TTL cleanup",
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
    ttl_status = await verify_ttl_index()
    return {
        "message": "Intern Management AI Service",
        "version": "1.0.0",
        "status": "running",
        "ttl_cleanup": "active" if ttl_status else "manual_only",
        "cleanup_task_status": "running" if cleanup_task and not cleanup_task.done() else "stopped"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with TTL status"""
    try:
        db = get_database()
        # Test database connection
        await db.command("ping")
        
        # Check TTL status
        ttl_working = await verify_ttl_index()
        
        return {
            "status": "healthy",
            "database": "connected",
            "ttl_index": "active" if ttl_working else "not_found",
            "automatic_cleanup": "enabled" if ttl_working else "disabled",
            "cleanup_task_running": cleanup_task and not cleanup_task.done(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "ttl_index": "unknown",
            "cleanup_task_running": False,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/stats")
async def get_stats():
    """Get database statistics including TTL status"""
    try:
        stats = await get_database_stats()
        
        # Add cleanup task status to stats
        ttl_status = await verify_ttl_index()
        
        if stats:
            stats["cleanup_system"] = {
                "ttl_index_active": ttl_status,
                "manual_task_running": cleanup_task and not cleanup_task.done(),
                "cleanup_frequency": "Every 1 hour (backup to TTL)",
                "automatic_deletion": "24 hours via TTL index" if ttl_status else "Manual only"
            }
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )

# New endpoint to check TTL and cleanup system status
@app.get("/api/cleanup/status")
async def get_cleanup_status():
    """Get detailed status of the TTL and cleanup system"""
    ttl_active = await verify_ttl_index()
    
    return {
        "ttl_index": {
            "active": ttl_active,
            "expiry_time": "24 hours",
            "status": "Automatic deletion enabled" if ttl_active else "TTL index not found"
        },
        "manual_cleanup": {
            "task_running": cleanup_task and not cleanup_task.done(),
            "frequency": "Every 1 hour",
            "purpose": "Backup to TTL + Session cleanup",
            "age_threshold": "24+ hours"
        },
        "recommendation": "TTL handles most cleanup automatically" if ttl_active else "Relying on manual cleanup only"
    }

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
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        if work_update.work_status == WorkStatus.ON_LEAVE:
            # ON LEAVE: Save directly to permanent collection
            work_updates_collection = db[Config.WORK_UPDATES_COLLECTION]
            date_based_query = {"userId": work_update.userId, "update_date": today_date}
            existing_update = await work_updates_collection.find_one(date_based_query)

            update_dict = work_update.dict(exclude={"id"})
            update_dict["update_date"] = today_date
            update_dict["submittedAt"] = datetime.now()
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
            # TTL index will automatically delete after 24 hours
            update_dict = work_update.dict(exclude={"id"})
            update_dict["update_date"] = today_date
            update_dict["submittedAt"] = datetime.now()
            update_dict["status"] = "pending_followup"  
            update_dict["followupCompleted"] = False

            # Use database function to create temp work update
            temp_work_update_id = await create_temp_work_update(update_dict)
            
            logger.info(f"WORKING work update saved to temp collection (TTL: 24h): {temp_work_update_id}")
            
            return {
                "message": "Work update saved temporarily. Complete follow-up within 24 hours to finalize.",
                "tempWorkUpdateId": temp_work_update_id,  
                "redirectToFollowup": True,
                "isOnLeave": False,
                "ttl_expiry": "24 hours from now"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating work update: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create work update: {str(e)}"
        )

# Start follow-up session using TEMP work update
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
            raise HTTPException(
                status_code=404, 
                detail="Temporary work update not found (may have been auto-deleted after 24h)"
            )

        today_date = datetime.now().strftime('%Y-%m-%d')
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
            "createdAt": datetime.now(),
            "completedAt": None
        }
        await followup_collection.replace_one({"_id": session_date_id}, session_doc, upsert=True)

        logger.info(f"Follow-up session started with temp work update: {temp_work_update_id}")

        return {
            "message": "Follow-up session started",
            "sessionId": session_date_id,
            "questions": questions,
            "reminder": "Complete within 24 hours before auto-deletion"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting follow-up session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start follow-up session: {str(e)}"
        )

# Complete follow-up and MOVE temp to permanent
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
            raise HTTPException(
                status_code=404, 
                detail="Temporary work update not found (may have been auto-deleted due to TTL expiry)"
            )

        # Complete the follow-up session
        session_update = {
            "answers": answers_update.answers,
            "status": SessionStatus.COMPLETED,
            "completedAt": datetime.now()
        }
        
        await followup_collection.update_one(
            {"_id": session_id},
            {"$set": session_update}
        )

        # MOVE temp work update to permanent collection using database function
        final_work_update_id = await move_temp_to_permanent(
            session["tempWorkUpdateId"],
            {"completedAt": datetime.now()}
        )

        # Update session with permanent work update ID
        await followup_collection.update_one(
            {"_id": session_id},
            {"$set": {"workUpdateId": final_work_update_id}}
        )

        logger.info(f"Follow-up completed, work update finalized: {final_work_update_id}")
        
        return {
            "message": "Follow-up questions completed successfully. Work update finalized and saved permanently.",
            "sessionId": session_id,
            "workUpdateId": final_work_update_id,
            "workUpdateCompleted": True,
            "note": "Work update moved from temporary to permanent storage"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete follow-up: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete follow-up: {str(e)}"
        )

# Manual cleanup endpoint (backup to automatic TTL)
@app.delete("/api/temp-work-updates/cleanup")
async def cleanup_abandoned_temp_updates_endpoint():
    """Manually trigger cleanup of temporary work updates (backup to TTL)"""
    try:
        ttl_active = await verify_ttl_index()
        result = await cleanup_abandoned_temp_updates(24)
        
        deleted_temp = result.get("deleted_temp_updates", 0)
        deleted_sessions = result.get("deleted_sessions", 0)
        
        return {
            "message": f"Manual cleanup completed. Cleaned up {deleted_temp} temp updates and {deleted_sessions} sessions",
            "deleted_temp_updates": deleted_temp,
            "deleted_sessions": deleted_sessions,
            "ttl_status": "active" if ttl_active else "inactive",
            "note": "TTL index handles most cleanup automatically" if ttl_active else "Manual cleanup is primary method"
        }
        
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
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