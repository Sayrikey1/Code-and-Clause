# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from config.database import engine
from models import models
from routers import auth, chatbot
from rag.query_engine import lifespan

# Load environment variables
load_dotenv()

# Initialize the FastAPI application with the lifespan context manager
app = FastAPI(lifespan=lifespan)

# Create all database tables
models.Base.metadata.create_all(bind=engine)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust the origins to restrict access as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chatbot.router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Hello World"}


# ─── API ENDPOINTS ───────────────────────────────────────────────────────────
# def get_query_engine(request: Request):
#     """Dependency to get the query engine from the app state."""
#     if not hasattr(request.app.state, "index"):
#         raise RuntimeError("RAG index not initialized")
#     return request.app.state.index.as_query_engine()

# @app.get("/")
# async def root():
#     """Health check endpoint."""
#     return {"status": "ok", "message": "RAG Engine is running"}

# @app.post("/query/")
# async def query(request: Request, query_engine=Depends(get_query_engine)):
#     """Query endpoint to search the RAG index."""
#     data = await request.json()
#     query_text = data.get("query")
    
#     if not query_text:
#         return {"error": "No query provided"}
    
#     try:
#         response = query_engine.query(query_text)
#         return {
#             "response": str(response),
#             "sources": [node.metadata for node in response.source_nodes]
#         }
#     except Exception as e:
#         logger.error(f"Query error: {e}")
#         return {"error": f"Query failed: {str(e)}"}

# # Run with: uvicorn main:app --reload
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
