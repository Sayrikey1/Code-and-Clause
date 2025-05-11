# Standard library imports
from contextlib import asynccontextmanager
import logging
import os
import time
from typing import Any, List, Sequence

# Third-party imports
from dotenv import load_dotenv
from fastapi import FastAPI, Request
import torch

# Google Gemini client
import google.generativeai as genai

# llama_index imports
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.readers.file import PDFReader
from llama_index.vector_stores.postgres import PGVectorStore

# Sentence Transformers (for model saving)
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger("rag_engine")

# ─── Environment & Device ──────────────────────────────────────────────────────
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("Set GOOGLE_API_KEY in .env to use Gemini API")
genai.configure(api_key=GOOGLE_API_KEY)

BASE_PDF_DIR = os.getenv("PDF_INPUT_DIR", "rag/data/NITDA")

def initialize_vector_db():
    try:
        logger.info("Initializing PostgreSQL vector store")
        vector_store = PGVectorStore.from_params(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", "5432")),
            database=os.getenv("PG_DATABASE", "rag_database"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", "postgres"),
            table_name=os.getenv("PG_TABLE_NAME", "rag_documents"),
            embed_dim=int(os.getenv("EMBED_DIM", "768")),
        )
        return vector_store
    except Exception as e:
        logger.error(f"Failed to initialize vector DB: {e}", exc_info=True)
        raise e

def load_all_pdfs_from_folder(folder_path: str):
    reader = PDFReader()
    all_docs = []
    if not os.path.exists(folder_path):
        logger.warning(f"PDF directory does not exist: {folder_path}")
        return all_docs

    for root, _, files in os.walk(folder_path):
        for fname in files:
            if fname.lower().endswith(".pdf"):
                path = os.path.join(root, fname)
                try:
                    docs = reader.load_data(file=path)
                    all_docs.extend(docs)
                    logger.info(f"Loaded {len(docs)} docs from {path}")
                except Exception as e:
                    logger.warning(f"Failed to read {path}: {str(e)}")
    return all_docs

def load_or_create_index(docs=None, embed_model=None, force_reload=False):
    try:
        vector_store = initialize_vector_db()
        if force_reload:
            if docs is None or embed_model is None:
                raise ValueError("Documents and embed_model are required on force reload")
            logger.info("Creating new vector store index...")
            index = VectorStoreIndex.from_documents(
                docs,
                vector_store=vector_store,
                embed_model=embed_model
            )
            logger.info("Index created")
            return index
        else:
            logger.info("Loading index from vector store...")
            return VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=embed_model
            )
    except Exception as e:
        logger.error(f"Error in load_or_create_index: {str(e)}", exc_info=True)
        raise e

global_index = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_index
    try:
        start_time = time.time()
        if global_index is not None and os.getenv("FORCE_RELOAD_INDEX", "false").lower() != "true":
            logger.info("Using cached index")
            app.state.index = global_index
            yield
            return

        # ─── Embedding Model Loading (with local cache support) ────────────────
        HF_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
        LOCAL_MODEL_PATH = os.path.join("cached_models", HF_MODEL_NAME.replace("/", "_"))
        os.makedirs("cached_models", exist_ok=True)

        if os.path.exists(LOCAL_MODEL_PATH) and os.listdir(LOCAL_MODEL_PATH):
            logger.info(f"Loading embedding model from local cache: {LOCAL_MODEL_PATH}")
            embed_model = HuggingFaceEmbedding(
                model_name=LOCAL_MODEL_PATH,
                device=DEVICE
            )
        else:
            logger.info(f"Downloading embedding model: {HF_MODEL_NAME}")
            embed_model = HuggingFaceEmbedding(
                model_name=HF_MODEL_NAME,
                device=DEVICE
            )
            SentenceTransformer(HF_MODEL_NAME).save(LOCAL_MODEL_PATH)
            logger.info(f"Model saved locally to: {LOCAL_MODEL_PATH}")

        # ─── Gemini LLM ─────────────────────────────────────────────────────────
        llm = Gemini(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            api_key=GOOGLE_API_KEY,
            temperature=0.3,
            max_tokens=1024
        )

        # ─── Settings ───────────────────────────────────────────────────────────
        Settings.llm = llm
        Settings.embed_model = embed_model
        Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
        Settings.num_output = 2048
        Settings.context_window = 4000

        # ─── Index Creation/Loading ─────────────────────────────────────────────
        force_reload = os.getenv("FORCE_RELOAD_INDEX", "false").lower() == "true"
        if force_reload:
            logger.info("Force reload enabled. Reading and indexing PDFs...")
            docs = load_all_pdfs_from_folder(BASE_PDF_DIR)
            index = load_or_create_index(docs=docs, embed_model=embed_model, force_reload=True)
        else:
            index = load_or_create_index(embed_model=embed_model)

        app.state.index = index
        global_index = index

        logger.info(f"Application startup complete in {time.time() - start_time:.2f}s")
        yield
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise e

def get_query_engine(request: Request):
    logger.debug("Query engine requested")
    if not hasattr(request.app.state, "index"):
        raise RuntimeError("RAG index not initialized")
    return request.app.state.index.as_query_engine()
