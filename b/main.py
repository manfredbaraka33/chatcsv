from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from uuid import uuid4
from models.agent_state import AgentState
from services.data_quality import generate_dqr_and_context
from services.llm_workflow import build_workflow
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Analysis Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# ⚙️ Simple in-memory session cache
# -----------------------------
session_store = {}

@app.get("/")
async def health_check():
    """Health check endpoint to verify server is running."""
    return {"message": "ChatCSV API is running ✅"}

# ----------------------------------------
# 🧾 Phase 1: Upload CSV + Preprocess
# ----------------------------------------

@app.post("/upload")
async def upload_csv(
    file: UploadFile,
    hasHeader: str = Form("yes"),
    headerRowIndex: int = Form(0)
):
    try:
        contents = await file.read()

        # Determine header handling
        header_param = 0 if hasHeader == "yes" else headerRowIndex
        
        # Read CSV
        df = pd.read_csv(io.BytesIO(contents), header=header_param)
        
    except Exception as e:
        logger.error(f"CSV parsing error: {e}")
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {e}")

    # Generate data quality report and context
    DQR, context = generate_dqr_and_context(df)
    session_id = str(uuid4())

    # Store session data
    session_store[session_id] = {
        "df": df,
        "context": context,
        "dqr": DQR,
    }

    logger.info(f"New session created: {session_id} with {len(df)} rows.")

    return {
        "status": "ready",
        "session_id": session_id,
        "summary": {
            "rows": len(df),
            "columns": list(df.columns),
            "dqr_preview": DQR[:300],
        },
    }


# ----------------------------------------
# 💬 Phase 2: Chat and Workflow Execution
# ----------------------------------------

@app.post("/chat")
async def chat(session_id: str = Form(...), query: str = Form(...)):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid or expired session_id")

    df = session["df"]
    context = session["context"]

    # Initialize the agent state
    state = AgentState(
        user_query=query,
        df=df,
        dqr_report=context,
        code_result="",
        error="",
        generated_code="",
        retries=0,
    )

    # Build and compile the LangGraph workflow
    workflow = build_workflow()
    logger.info(f"Starting workflow for session {session_id} with query: {query[:50]}")

    async def event_stream():
        """
        Asynchronous generator (SSE) for streaming the final answer.
        It monitors the LangGraph steps until the 'humanize_answer' node is hit.
        """
        final_state = None
        
        # Use .astream for asynchronous graph execution
        async for step in workflow.astream(state, config={"recursion_limit": 5}):
            final_state = step
            
            # We are primarily interested in the output of the humanize_answer node
            if "humanize_answer" in step:
                # Extract the code_result from the final node
                final_result = step["humanize_answer"].get("code_result", "")
                
                # --- NEW RECTIFICATION LOGIC START ---
                
                # If the final result is empty, substitute a helpful message
                if not final_result:
                    logger.warning("Workflow finished successfully, but the final result was empty. Suggesting LLM output fix.")
                    final_result = (
                        "✅ The analysis code ran successfully, but the answer was blank. "
                        "Please ensure the analysis code prints the final result."
                    )
                
                logger.info(f"Final streamed result length: {len(final_result)}. Content: {final_result[:50]}...")
                
                # Stream the final result chunk (now guaranteed to be non-empty if successful)
                yield f"data: {json.dumps({'delta': final_result})}\n\n"
                    
                # Break the loop immediately after getting the final humanized answer
                break 
                # --- NEW RECTIFICATION LOGIC END ---

        # Handle max retries/final error state after the loop finishes
        if final_state and final_state.get('error'):
             error_msg = f'Error: Could not resolve the query after max retries. Last error: {final_state["error"]}'
             yield f"data: {json.dumps({'delta': error_msg})}\n\n"

        # Send the final 'done' signal to the client
        yield f"data: {json.dumps({'done': True})}\n\n"
        logger.info(f"Workflow finished for session {session_id}.")


    # This line MUST be outside the event_stream function.
    return StreamingResponse(event_stream(), media_type="text/event-stream")
