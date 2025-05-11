# Fix for chatbot.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from collections import deque
from typing import Any, Optional

import os, mimetypes, tempfile, httpx, logging
from config.database import get_session
from models.models import ChatbotInteraction, User
from models.schema import ChatbotRequest, ChatbotResponse
from rag.query_engine import get_query_engine
from routers.auth import get_current_user
from routers.helpers.helper import extract_urls, handle_content

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
MAX_HISTORY = 5
prompt_header = """
  you are Code&Clause, designed to assist with the clearance of Information Technology projects by public institutions.
  You can also provide efficient, enjoyable, and secure service by processing applications, sending notices, verifying identity, resolving disputes, managing risk, and improving NITDA services.
  You can also help detect, prevent, or remediate violations of laws, regulations, standards, guidelines, and frameworks, as well as track information breaches and manage information technology and physical infrastructure.
"""

@router.post(
    "/chatbot/",
    response_model=ChatbotResponse,
    summary="Chat with text, file, or link",
)
async def chatbot_post(
    user_input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    query_engine=Depends(get_query_engine),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Any:
    logger.info(f"Received request with user_input: {user_input}, file: {file is not None}")
    
    if not user_input and not file:
        raise HTTPException(400, "Provide text, file, or URL links")

    # load recent history (for logging)
    past = (
        db.query(ChatbotInteraction)
          .filter_by(user_id=current_user.id)
          .order_by(ChatbotInteraction.timestamp.desc())
          .limit(MAX_HISTORY)
          .all()
    )
    history = deque(maxlen=MAX_HISTORY)
    for msg in reversed(past):
        history.extend([msg.user_input, msg.response])

    response_texts: list[str] = []
    temp_files_to_remove = []

    try:
        # 1) If a file is uploaded
        if file:
            logger.info(f"Processing file: {file.filename}, content type: {file.content_type}")
            suffix = os.path.splitext(file.filename)[1]
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            content = await file.read()
            tmp.write(content)
            tmp.flush()
            tmp.close()
            temp_files_to_remove.append(tmp.name)

            mime = file.content_type or mimetypes.guess_type(file.filename)[0]
            logger.info(f"File MIME type: {mime}")
            
            try:
                response = await handle_content(tmp.name, mime, user_input or "Analyze this file.")
                if response:
                    response_texts.append(response)
                    logger.info("File processing succeeded")
                else:
                    logger.warning("File processing returned empty response")
                    response_texts.append("I couldn't process this file type properly.")
            except Exception as e:
                logger.error(f"Error handling file content: {str(e)}", exc_info=True)
                response_texts.append(f"Error processing file: {str(e)}")

        # 2) URLs in the text
        if user_input:
            urls = extract_urls(user_input)
            logger.info(f"Extracted URLs: {urls}")
            
            for url in urls:
                try:
                    # guess mime from headers or extension
                    head = httpx.head(url, timeout=10.0)
                    mime = head.headers.get("Content-Type", mimetypes.guess_type(url)[0])
                    logger.info(f"URL MIME type: {mime}")
                    
                    url_response = await handle_content(url, mime, user_input)
                    if url_response:
                        response_texts.append(url_response)
                    else:
                        response_texts.append(f"Couldn't process URL: {url}")
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
                    response_texts.append(f"Error processing URL {url}: {str(e)}")

        response_texts = [r.strip() for r in response_texts if r and r.strip() and "Empty Response" not in r]
        
        # 3) Fallback to text-only RAG if still nothing
        if not response_texts and user_input:
            logger.info("Falling back to text-only RAG")
            try:
                query_text = prompt_header + "\n" + user_input
                out = query_engine.query(query_text)
                if out and getattr(out, "response", "").strip():
                    response_texts.append(out.response.strip())
                    logger.info("RAG query succeeded")
                else:
                    logger.warning("RAG query returned empty response")
                    response_texts.append("I couldn't generate a good response for your query.")
            except Exception as e:
                logger.error(f"Error in RAG query: {e}", exc_info=True)
                response_texts.append(f"Error generating response: {e}")
        
        # 4) Assemble final response
        final_resp = "\n\n".join(response_texts) or "I'm having trouble generating a response right now."
        logger.info(f"Final response generated with length: {len(final_resp)}")

        # persist
        record = ChatbotInteraction(
            user_id=current_user.id,
            user_input=user_input or (file.filename if file else "<empty>"),
            response=final_resp,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()

        return ChatbotResponse(
            user_input=record.user_input,
            response=final_resp,
            timestamp=record.timestamp,
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in chatbot endpoint: {str(e)}", exc_info=True)
        raise HTTPException(500, f"An error occurred: {str(e)}")
    
    finally:
        # Clean up temporary files in background
        for tmp_file in temp_files_to_remove:
            background_tasks.add_task(os.remove, tmp_file)


@router.get("/chatbot/history/", response_model=None)
async def get_chat_history(
    db: Session = Depends(get_session), current_user: User = Depends(get_current_user)
) -> Any:
    chat_history = (
        db.query(ChatbotInteraction)
        .filter(ChatbotInteraction.user_id == current_user.id)
        .order_by(ChatbotInteraction.timestamp.asc())
        .all()
    )

    return chat_history