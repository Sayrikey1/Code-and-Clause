import os
import re
import io
import pathlib
import tempfile
import mimetypes
import httpx
import logging
from google import genai, generativeai
from google.genai import types
from typing import Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_urls(text: Optional[str]) -> list[str]:
    if not text:
        return []
    # basic http(s) URL regex
    return re.findall(r'(https?://[^\s]+)', text)

# Initialize Google API client
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable is not set")
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    
    client = genai.Client(api_key=api_key)
    logger.info("Google AI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Google AI client: {str(e)}", exc_info=True)
    raise

async def handle_content(
    source: str,            # either local path or a URL
    mime_type: str|None,    # hint, e.g. 'application/pdf'
    user_input: Optional[str] = None
) -> str:
    logger.info(f"Handling content from {source}, mime_type: {mime_type}")
    
    if not mime_type:
        logger.warning(f"No MIME type provided for {source}, will try to guess")
        mime_type = mimetypes.guess_type(source)[0]
        logger.info(f"Guessed MIME type: {mime_type}")
    
    contents: list[Any] = []
    temp_files = []
    
    try:
        # — PDF (remote or local) via in‑memory BytesIO for large files
        if mime_type == "application/pdf":
            logger.info("Processing PDF content")
            # fetch remote if it's a URL
            if source.startswith("http"):
                try:
                    response = httpx.get(source, timeout=30.0)
                    data = response.content
                except Exception as e:
                    logger.error(f"Error fetching PDF from URL {source}: {str(e)}", exc_info=True)
                    return f"Error fetching PDF: {str(e)}"
            else:
                try:
                    with open(source, "rb") as f:
                        data = f.read()
                except Exception as e:
                    logger.error(f"Error reading PDF file {source}: {str(e)}", exc_info=True)
                    return f"Error reading PDF file: {str(e)}"
            
            # wrap in Part directly
            part = types.Part.from_bytes(data=data, mime_type="application/pdf")
            contents.append(part)
            contents.append(user_input or "Summarize this document.")
            
        # — Image
        elif mime_type and mime_type.startswith("image/"):
            logger.info("Processing image content")
            try:
                # local or remote path to file
                if source.startswith("http"):
                    resp = httpx.get(source, timeout=30.0)
                    tmp = tempfile.NamedTemporaryFile(suffix=pathlib.Path(source).suffix, delete=False)
                    tmp.write(resp.content)
                    tmp.flush()
                    tmp.close()
                    temp_files.append(tmp.name)
                    file_to_use = tmp.name
                else:
                    file_to_use = source
                
                logger.info(f"Uploading image file: {file_to_use}")
                upload_ref = client.files.upload(file=file_to_use)
                
                contents.append(upload_ref)
                contents.append(user_input or "Caption this image.")
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}", exc_info=True)
                return f"Error processing image: {str(e)}"
            
        # — Audio
        elif mime_type and mime_type.startswith("audio/"):
            logger.info("Processing audio content")
            try:
                if source.startswith("http"):
                    resp = httpx.get(source, timeout=30.0)
                    tmp = tempfile.NamedTemporaryFile(suffix=pathlib.Path(source).suffix, delete=False)
                    tmp.write(resp.content)
                    tmp.flush()
                    tmp.close()
                    temp_files.append(tmp.name)
                    file_to_use = tmp.name
                else:
                    file_to_use = source
                
                logger.info(f"Uploading audio file: {file_to_use}")
                upload_ref = client.files.upload(file=file_to_use)
                
                contents.append(user_input or "Describe this audio clip.")
                contents.append(upload_ref)
            except Exception as e:
                logger.error(f"Error processing audio: {str(e)}", exc_info=True)
                return f"Error processing audio: {str(e)}"
            
        # — Plain text / HTML / JSON
        elif mime_type and (mime_type.startswith("text/") or "json" in mime_type):
            logger.info("Processing text content")
            try:
                if source.startswith("http"):
                    resp = httpx.get(source, timeout=30.0)
                    text_data = resp.text
                else:
                    with open(source, "r", encoding="utf-8", errors="ignore") as f:
                        text_data = f.read()
                
                contents.append(text_data)
                contents.append(user_input or "Summarize this content.")
            except Exception as e:
                logger.error(f"Error processing text content: {str(e)}", exc_info=True)
                return f"Error processing text content: {str(e)}"
        else:
            logger.warning(f"Unsupported MIME type: {mime_type or 'unknown'}")
            return f"Unsupported content type: {mime_type or 'unknown'}"

        # generate with Gemini
        logger.info("Calling Gemini API")
        try:
            # Try with safety settings adjusted if needed
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            safety_settings = {
                "HARASSMENT": "BLOCK_NONE",
                "HATE": "BLOCK_NONE",
                "SEXUAL": "BLOCK_NONE",
                "DANGEROUS": "BLOCK_NONE",
            }
            
            try:
                # First try with default settings
                resp = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=contents,
                )
            except Exception as e:
                if "blocked" in str(e).lower() or "safety" in str(e).lower():
                    logger.warning(f"Initial generation blocked by safety settings, retrying with adjusted settings: {str(e)}")
                    # Try with adjusted safety settings
                    resp = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=contents,
                        safety_settings=safety_settings
                    )
                else:
                    raise
            
            if hasattr(resp, 'text') and resp.text:
                logger.info(f"Successfully generated response, length: {len(resp.text)}")
                return resp.text
            else:
                logger.warning("Empty response from Gemini API")
                return "I couldn't generate a response for this content."
                
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {str(e)}", exc_info=True)
            return f"Error generating response: {str(e)}"
    
    except Exception as e:
        logger.error(f"Unexpected error in handle_content: {str(e)}", exc_info=True)
        return f"An error occurred while processing your request: {str(e)}"
    
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_file}: {str(e)}")