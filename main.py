# Query Planner
# Deep Retrieval
# Evidence Extraction
# Deep Writer
# Critic

import asyncio
import time
import uuid

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from pydantic import (
    BaseModel,
    Field
)

from pipeline import (
    run_research_pipeline
)

# FASTAPI

app = FastAPI(

    title=
    "Research Intelligence API",

    description=
    (
        "Deep multi-source "
        "research engine"
    ),

    version="3.0.0"
)

# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# REQUEST MODEL
class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=600
    )
# ROOT
@app.get("/")
async def root():

    return {
        "service": "Research Intelligence API",
        "version": "3.0.0",
        "status": "running",
        "docs": "/docs"
    }

# HEALTH
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "pipeline": "active",
        "architecture": [
            "Query Planner",
            "Deep Retrieval",
            "Evidence Extraction",
            "Deep Writer",
            "Critic"
        ]
    }

# SYSTEM

@app.get("/system")
async def system():
    return {
        "capabilities": [
            "Academic Research",
            "Google Scholar",
            "Arxiv",
            "PubMed",
            "Wikipedia",
            "Evidence Grounding",
            "Deep Research",
            "Critic Evaluation"
        ],
        "outputs": [
            "txt",
            "pdf",
            "docx"
        ]
    }

# MAIN RESEARCH API

@app.post(
    "/api/v1/research"
)
async def research(
    request:
    ResearchRequest
):
    request_id = str(
        uuid.uuid4()
    )[:8]
    start = (
        time.time()
    )

    try:
        topic = (
            request.topic
            .strip()
        )

        result = await (
            asyncio.to_thread(
                run_research_pipeline,
                topic
            )
        )

        if (
            result.get( "status") == "failed"
        ):
            raise HTTPException( status_code=500, detail= result.get("error"))

        total_time = round(
            time.time()- start,2)

        return {

            "status": "success",

            "request_id": request_id,

            "topic": topic,

            "query_plan": result.get(
                "query_plan",
                {}
            ),

            "report":
            result.get(
                "report",
                ""
            ),

            "feedback":
            result.get(
                "feedback",
                ""
            ),

            "logs":
            result.get(
                "logs",
                []
            ),

            "sources":
            len(
                result.get(
                    "sources",
                    []
                )
            ),

            "scraped_sources":
            len(
                result.get(
                    "scraped_sources",
                    []
                )
            ),

            "metadata": {

                **result.get(
                    "metadata",
                    {}
                ),

                "api_time":
                total_time
            }
        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail={

                "request_id":
                request_id,

                "error":
                str(e)
            }
        )

# FILE UPLOAD READY

@app.post(
    "/api/v1/upload"
)
async def upload_file(

    file:
    UploadFile = File(...)
):

    return {

        "filename":
        file.filename,

        "status":
        "uploaded",

        "message":
        (
            "PDF ingestion "
            "coming next"
        )
    }

# RUN
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "main:app",

        host="0.0.0.0",

        port=8000,

        reload=True
    )


# python main.py
# http://localhost:8000/docs