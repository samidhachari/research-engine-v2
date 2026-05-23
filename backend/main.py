
import os
import uuid
import shutil
import logging
from datetime import datetime
from typing import (
    List,
    Optional,
    Dict,
    Any
)

from dotenv import (
    load_dotenv
)

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    BackgroundTasks
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from fastapi.responses import (
    StreamingResponse
)

from pydantic import ( BaseModel,  Field )

from pymongo import (
    MongoClient
)

from pymongo.errors import (
    ConnectionFailure
)

from backend.pipeline import (
    run_research_pipeline
)

from backend.tools import (
    ingest_pdfs,
    PDF_UPLOAD_DIR
)

# LOAD ENV

load_dotenv()

# CONFIG

APP_NAME = (
    "Research Engine API"
)

APP_VERSION = (
    "3.0.0"
)

MAX_PDF_UPLOAD = 150

MAX_FILE_SIZE_MB = 100

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)

DATABASE_NAME = (
    "research_engine"
)

# LOGGING

logging.basicConfig(
    level=logging.INFO,
    format=(

        "%(asctime)s | "

        "%(levelname)s | "

        "%(message)s"
    )
)

logger = logging.getLogger(
    "ResearchEngineAPI"
)

# FASTAPI APP

app = FastAPI(

    title=APP_NAME,

    description=(
        "World-Class "
        "Research Engine API"
    ),

    version=APP_VERSION
)

# CORS

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://localhost:3000",  # React

        "http://localhost:5173",  # Vite

        "http://localhost:8501",  # Streamlit

        "*"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)

# MONGODB

mongo_client = None

db = None

research_collection = None

pdf_collection = None

observability_collection = None

# CONNECT DB

def connect_mongodb():

    global mongo_client
    global db
    global research_collection
    global pdf_collection
    global observability_collection

    try:

        mongo_client = (
            MongoClient(
                MONGO_URI
            )
        )

        mongo_client.admin.command(
            "ping"
        )

        db = mongo_client[
            DATABASE_NAME
        ]

        research_collection = (
            db[
                "research_sessions"
            ]
        )

        pdf_collection = (
            db[
                "uploaded_pdfs"
            ]
        )

        observability_collection = (
            db[
                "observability_logs"
            ]
        )

        logger.info(
            "MongoDB Connected"
        )

    except ConnectionFailure as e:

        logger.error(
            f"MongoDB Failed: "
            f"{str(e)}"
        )

        raise Exception(
            "MongoDB connection failed."
        )

# STARTUP

@app.on_event(
    "startup"
)
async def startup_event():

    logger.info(
        "=" * 70
    )

    logger.info(
        "STARTING "
        "RESEARCH ENGINE"
    )

    logger.info(
        "=" * 70
    )

    connect_mongodb()

    os.makedirs(
        PDF_UPLOAD_DIR,
        exist_ok=True
    )

    logger.info(
        "Startup Complete"
    )

# TIMESTAMP

def timestamp():

    return datetime.utcnow().isoformat()

# REQUEST SCHEMA

class ResearchRequest(
    BaseModel
):

    topic: str = Field(

        ...,

        min_length=3,

        max_length=1000
    )

    mode: str = Field(

        default="research",

        description=(

            "quick | "
            "research | "
            "deep"
        )
    )

    filters: Optional[
        Dict[str, Any]
    ] = None

# RESPONSE SCHEMA

class ResearchResponse(
    BaseModel
):

    status: str

    topic: str

    report: str

    feedback: str

    source_explorer: list

    metadata: dict

    logs: list

# SAVE SESSION

def save_research_session(
    result
):

    try:

        session_data = {

            "session_id":
            str(uuid.uuid4()),

            "topic":
            result.get(
                "topic"
            ),

            "report":
            result.get(
                "report"
            ),

            "feedback":
            result.get(
                "feedback"
            ),

            "source_count":
            len(
                result.get(
                    "source_explorer",
                    []
                )
            ),

            "metadata":
            result.get(
                "metadata",
                {}
            ),

            "created_at":
            timestamp()
        }

        research_collection.insert_one(
            session_data
        )

    except Exception as e:

        logger.warning(
            f"Session Save "
            f"Failed: "
            f"{str(e)}"
        )

# SAVE OBSERVABILITY

def save_observability_log(
    result
):

    try:

        observability_collection.insert_one({

            "topic":
            result.get(
                "topic"
            ),

            "metadata":
            result.get(
                "metadata"
            ),

            "logs":
            result.get(
                "logs"
            ),

            "created_at":
            timestamp()
        })

    except Exception as e:

        logger.warning(
            f"Observability Save "
            f"Failed: "
            f"{str(e)}"
        )



import asyncio
import json

# RESEARCH ENDPOINT

@app.post(
    "/research",
    response_model=
    ResearchResponse
)
async def start_research(
    request: ResearchRequest
):

    try:

        topic = (
            request.topic
            .strip()
        )

        if not topic:

            raise HTTPException(

                status_code=400,

                detail=(
                    "Topic cannot "
                    "be empty."
                )
            )

        logger.info(
            "=" * 70
        )

        logger.info(
            f"Research Request "
            f"| Topic={topic}"
        )

        logger.info(
            f"Mode="
            f"{request.mode}"
        )

        logger.info(
            "=" * 70
        )

        # PIPELINE EXECUTION

        result = await asyncio.to_thread(

            run_research_pipeline,

            topic,

            request.mode,

            request.filters
        )

        if (

            result.get(
                "status"
            ) == "failed"
        ):

            raise HTTPException(

                status_code=500,

                detail=result.get(
                    "error",
                    "Pipeline Failed"
                )
            )

        # SAVE

        result["topic"] = (
            topic
        )

        save_research_session(
            result
        )

        save_observability_log(
            result
        )

        logger.info(
            "Research Completed"
        )

        return ResearchResponse(

            status="success",

            topic=topic,

            report=result.get(
                "report",
                ""
            ),

            feedback=result.get(
                "feedback",
                ""
            ),

            source_explorer=
            result.get(
                "source_explorer",
                []
            ),

            metadata=result.get(
                "metadata",
                {}
            ),

            logs=result.get(
                "logs",
                []
            )
        )

    except HTTPException:
        raise

    except Exception as e:

        logger.error(
            f"Research Failed: "
            f"{str(e)}"
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )

# STREAMING ENDPOINT

@app.post(
    "/research/stream"
)
async def research_stream(
    request: ResearchRequest
):

    async def event_generator():

        try:

            yield (
                "data: "
                +
                json.dumps({

                    "stage":
                    "planner",

                    "status":
                    "started"
                })
                +
                "\n\n"
            )

            yield (
                "data: "
                +
                json.dumps({

                    "stage":
                    "retrieval",

                    "status":
                    "started"
                })
                +
                "\n\n"
            )

            result = await asyncio.to_thread(

                run_research_pipeline,

                request.topic,

                request.mode,

                request.filters
            )

            yield (
                "data: "
                +
                json.dumps({

                    "stage":
                    "completed",

                    "status":
                    "success",

                    "result":
                    result
                })
                +
                "\n\n"
            )

        except Exception as e:

            yield (
                "data: "
                +
                json.dumps({

                    "status":
                    "failed",

                    "error":
                    str(e)
                })
                +
                "\n\n"
            )

    return StreamingResponse(

        event_generator(),

        media_type=
        "text/event-stream"
    )



@app.post(
    "/upload-pdfs"
)
async def upload_pdfs(

    files:
    List[UploadFile]
    = File(...)
):

    try:

        if len(files) > (
            MAX_PDF_UPLOAD
        ):

            raise HTTPException(

                status_code=400,

                detail=(
                    f"Maximum "
                    f"{MAX_PDF_UPLOAD} "
                    f"PDFs allowed."
                )
            )

        saved_paths = []

        for file in files:

            if not (
                file.filename
                .endswith(".pdf")
            ):

                continue

            file_path = (
                os.path.join(

                    PDF_UPLOAD_DIR,

                    file.filename
                )
            )

            with open(

                file_path,

                "wb"

            ) as buffer:

                shutil.copyfileobj(

                    file.file,

                    buffer
                )

            saved_paths.append(
                file_path
            )

            # SAVE PDF META

            pdf_collection.insert_one({

                "filename":
                file.filename,

                "path":
                file_path,

                "uploaded_at":
                timestamp()
            })

        # INGEST PDFs

        ingestion_success = (
            ingest_pdfs(
                saved_paths
            )
        )

        if not ingestion_success:

            raise HTTPException(

                status_code=500,

                detail=(
                    "PDF ingestion "
                    "failed."
                )
            )

        logger.info(
            f"PDF Upload Success "
            f"| Count="
            f"{len(saved_paths)}"
        )

        return {

            "status":
            "success",

            "pdfs_uploaded":
            len(saved_paths),

            "files":
            [
                os.path.basename(
                    p
                )
                for p in
                saved_paths
            ]
        }

    except Exception as e:

        logger.error(
            f"PDF Upload "
            f"Failed: "
            f"{str(e)}"
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )

# HISTORY

@app.get(
    "/history"
)
async def get_history():

    try:

        sessions = list(

            research_collection

            .find(

                {},

                {
                    "_id": 0
                }
            )

            .sort(

                "created_at",

                -1
            )

            .limit(30)
        )

        return {

            "status":
            "success",

            "count":
            len(sessions),

            "history":
            sessions
        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )

# HEALTH

@app.get(
    "/health"
)
async def health():

    mongo_status = (
        "connected"
        if mongo_client
        else "disconnected"
    )

    return {

        "status":
        "running",

        "service":
        APP_NAME,

        "version":
        APP_VERSION,

        "mongo":
        mongo_status,

        "timestamp":
        timestamp()
    }

# OBSERVABILITY

@app.get(
    "/metrics"
)
async def metrics():

    try:

        research_count = (
            research_collection
            .count_documents({})
        )

        pdf_count = (
            pdf_collection
            .count_documents({})
        )

        latest_logs = list(

            observability_collection

            .find(

                {},

                {"_id": 0}
            )

            .sort(

                "created_at",

                -1
            )

            .limit(5)
        )

        return {

            "status":
            "success",

            "metrics": {

                "research_sessions":
                research_count,

                "uploaded_pdfs":
                pdf_count,

                "recent_logs":
                latest_logs
            }
        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )

# ROOT

@app.get("/")
async def root():

    return {

        "message":
        "Research Engine "
        "API Running",

        "version":
        APP_VERSION,

        "docs":
        "/docs",

        "health":
        "/health"
    }

# LOCAL RUN

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "main:app",

        host="0.0.0.0",

        port=8000,

        reload=True
    )



