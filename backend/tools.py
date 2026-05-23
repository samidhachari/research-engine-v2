
import os
import re
import json
import time
import uuid
import faiss
import fitz
import queue
import arxiv
import httpx
import pickle
import logging
import requests
import warnings
import wikipedia
import numpy as np
import threading

from typing import (
    List,
    Dict,
    Any,
    Optional
)

from dotenv import load_dotenv
from tavily import TavilyClient
from scholarly import scholarly
from bs4 import BeautifulSoup
from Bio import Entrez

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential
)

from sentence_transformers import ( SentenceTransformer )

from langchain.tools import tool

warnings.filterwarnings(
    "ignore"
)

# ENVIRONMENT

load_dotenv()

TAVILY_API_KEY = os.getenv( "TAVILY_API_KEY" )

PUBMED_EMAIL = os.getenv( "PUBMED_EMAIL", "researchengine@gmail.com" )

if not TAVILY_API_KEY:
    raise ValueError( "TAVILY_API_KEY missing in .env" )

Entrez.email = PUBMED_EMAIL

# TAVILY CLIENT

tavily = TavilyClient( api_key=TAVILY_API_KEY)

# LOGGING

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)

logger = logging.getLogger( "ResearchEngineV3" )

# GLOBAL CONFIG

MAX_RETRIES = 3
REQUEST_TIMEOUT = 20
QUICK_MODE_LIMIT = 10
RESEARCH_MODE_LIMIT = 40
DEEP_MODE_LIMIT = 120
PDF_CHUNK_SIZE = 700
PDF_CHUNK_OVERLAP = 120
EMBEDDING_MODEL_NAME = ( "all-MiniLM-L6-v2")

VECTOR_STORE_DIR = ( "vector_store")

PDF_UPLOAD_DIR = ( "uploaded_pdfs")

os.makedirs( VECTOR_STORE_DIR, exist_ok=True )

os.makedirs( PDF_UPLOAD_DIR, exist_ok=True )

# EMBEDDING MODEL

logger.info( "Loading embedding model..." )

embedding_model = ( SentenceTransformer( EMBEDDING_MODEL_NAME ))

logger.info( "Embedding model loaded.")

# QUERY TYPE REGISTRY

ACADEMIC_KEYWORDS = [
    "research",
    "paper",
    "study",
    "scientific",
    "journal",
    "academic",
    "cryptography",
    "quantum",
    "biology",
    "chemistry",
    "physics",
    "healthcare",
    "genomics",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "transformer",
    "neural network",
    "artificial intelligence"
]

MARKET_KEYWORDS = [
    "market",
    "stock",
    "valuation",
    "startup",
    "forecast",
    "investment",
    "industry",
    "competition",
    "economy",
    "business",
    "revenue",
    "profit"
]

NEWS_KEYWORDS = [
    "latest",
    "today",
    "breaking",
    "recent",
    "news",
    "current",
    "this week",
    "update"
]

TECHNICAL_KEYWORDS = [
    "architecture",
    "system",
    "design",
    "api",
    "distributed systems",
    "compiler",
    "database",
    "firmware",
    "kernel",
    "infrastructure",
    "microservices",
    "kubernetes"
]

# TRUSTED SOURCE REGISTRY
# 100+ TRUST DOMAINS

TRUSTED_DOMAINS = {

    # GOVERNMENT
    ".gov": 10,
    "nist.gov": 10,
    "nih.gov": 10,
    "nsf.gov": 10,
    "nasa.gov": 10,
    "darpa.mil": 10,
    "energy.gov": 10,
    "europa.eu": 10,
    "gov.uk": 10,
    "who.int": 10,
    "un.org": 10,
    "oecd.org": 10,
    "worldbank.org": 10,
    "imf.org": 10,

    # UNIVERSITIES
    ".edu": 9,
    "mit.edu": 10,
    "stanford.edu": 10,
    "harvard.edu": 10,
    "berkeley.edu": 10,
    "cmu.edu": 10,
    "princeton.edu": 10,
    "ox.ac.uk": 10,
    "cam.ac.uk": 10,
    "ethz.ch": 10,

    # PAPERS
    "nature.com": 10,
    "science.org": 10,
    "ieee.org": 10,
    "acm.org": 10,
    "springer.com": 9,
    "springernature.com": 9,
    "arxiv.org": 9,
    "sciencedirect.com": 9,
    "pubmed.ncbi.nlm.nih.gov": 10,
    "ncbi.nlm.nih.gov": 10,
    "jstor.org": 9,
    "wiley.com": 8,
    "frontiersin.org": 8,
    "plos.org": 8,
    "semanticscholar.org": 9,

    # AI LABS
    "openai.com": 9,
    "anthropic.com": 9,
    "deepmind.google": 9,
    "research.google": 9,
    "microsoft.com/research": 9,
    "ai.meta.com": 9,
    "allenai.org": 9,
    "huggingface.co": 8,

    # BUSINESS
    "reuters.com": 9,
    "bloomberg.com": 8,
    "wsj.com": 8,
    "ft.com": 8,
    "economist.com": 8,
    "mckinsey.com": 9,
    "gartner.com": 9,
    "forbes.com": 7,
    "fortune.com": 7,
    "techcrunch.com": 7,
    "ycombinator.com": 8,

    # TECHNICAL DOCS
    "developer.nvidia.com": 8,
    "developer.apple.com": 8,
    "learn.microsoft.com": 8,
    "aws.amazon.com": 8,
    "cloud.google.com": 8,
    "react.dev": 8,
    "nodejs.org": 8,
    "docs.python.org": 8,

    # MEDICAL
    "mayoclinic.org": 9,
    "clevelandclinic.org": 9,
}

# PDF VECTOR DATABASE

PDF_VECTOR_INDEX = None
PDF_CHUNKS = []
PDF_METADATA = []

# TIMESTAMP

def timestamp():
    return time.strftime( "%Y-%m-%d %H:%M:%S")

# QUERY TYPE DETECTION

def detect_query_type( query: str):
    query_lower = query.lower()
    academic_score = sum(
        1 for k in
        ACADEMIC_KEYWORDS
        if k in query_lower
    )

    market_score = sum(
        1 for k in
        MARKET_KEYWORDS
        if k in query_lower
    )

    news_score = sum(
        1 for k in
        NEWS_KEYWORDS
        if k in query_lower
    )

    technical_score = sum(
        1 for k in
        TECHNICAL_KEYWORDS
        if k in query_lower
    )

    scores = {
        "academic": academic_score,
        "market": market_score,
        "news": news_score,
        "technical": technical_score
    }

    detected_type = max( scores, key=scores.get)

    logger.info(
        f"Detected Query Type: "
        f"{detected_type.upper()}"
    )

    return detected_type

# RESEARCH MODES

def get_mode_config( mode: str):

    mode = mode.lower()
    if mode == "quick":
        return {
            "max_sources": 10,
            "scholar_limit": 5,
            "arxiv_limit": 5,
            "pubmed_limit": 5,
            "deep_mode": False
        }
    elif mode == "research":
        return {
            "max_sources": 40,
            "scholar_limit": 15,
            "arxiv_limit": 15,
            "pubmed_limit": 10,
            "deep_mode": True
        }
    elif mode == "deep":
        return {
            "max_sources": 120,
            "scholar_limit": 40,
            "arxiv_limit": 35,
            "pubmed_limit": 25,
            "deep_mode": True
        }
    return {
        "max_sources": 40,
        "scholar_limit": 15,
        "arxiv_limit": 15,
        "pubmed_limit": 10,
        "deep_mode": True
    }
# TRUST SCORE

def get_trust_score( url: str):
    url = url.lower()
    for domain, score in ( TRUSTED_DOMAINS.items() ):
        if domain in url:
            return score
    return 5

# PDF TEXT EXTRACTION

def extract_pdf_text( pdf_path: str ):
    logger.info(
        f"Extracting PDF: "
        f"{pdf_path}"
    )

    try:
        doc = fitz.open(pdf_path)
        full_text = ""

        for page in doc:
            text = page.get_text()
            if text:
                full_text += ( text + "\n")

        logger.info(
            f"PDF Extraction Success | "
            f"Chars={len(full_text)}"
        )
        return full_text

    except Exception as e:
        logger.error(
            f"PDF Extraction Failed: "
            f"{str(e)}"
        )
        return ""

# TEXT CHUNKING
def chunk_text(text: str, chunk_size=PDF_CHUNK_SIZE, overlap=PDF_CHUNK_OVERLAP):
    chunks = []
    start = 0

    while start < len(text):
        end = ( start + chunk_size)
        chunk = text[start:end]
        chunks.append( chunk )
        start += ( chunk_size - overlap )

    return chunks

# PDF EMBEDDINGS

def embed_chunks(chunks: List[str]):
    logger.info( f"Embedding {len(chunks)} chunks...")

    embeddings = (
        embedding_model.encode(
            chunks,
            show_progress_bar=True
        )
    )

    return np.array(
        embeddings,
        dtype=np.float32
    )

# BUILD FAISS INDEX
def build_faiss_index( embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2( dimension)

    index.add( embeddings)
    return index


from tenacity import ( retry, stop_after_attempt, wait_exponential )
# RETRY CONFIG
@retry(
    stop=stop_after_attempt( MAX_RETRIES),
    wait=wait_exponential(
        multiplier=2,
        min=2,
        max=10
    )
)

# GOOGLE SCHOLAR SEARCH
def google_scholar_search( query: str, limit: int = 20, filters: dict = None):
    logger.info(
        f"[{timestamp()}] "
        f"Scholar Search Started: "
        f"{query}"
    )

    results = []
    try:
        search_query = ( scholarly.search_pubs( query ))
        for _ in range(limit):
            try:
                paper = next( search_query)
                bib = paper.get("bib", {})
                year = bib.get( "pub_year", "Unknown")
                citations = paper.get("num_citations", 0)

                # FILTERS

                if filters:
                    year_from = ( filters.get( "year_from"))
                    min_citations = ( filters.get( "min_citations", 0))
                    if ( year_from and year != "Unknown"):
                        if int(year) < year_from:
                            continue
                    if citations < min_citations:
                        continue

                results.append({
                    "id": str(uuid.uuid4()),
                    "source": "google_scholar",
                    "title": bib.get( "title", ""),
                    "url": paper.get( "pub_url",  ""),
                    "content": bib.get( "abstract", ""),
                    "authors": bib.get("author", []),
                    "year": year,
                    "citations": citations,
                    "published": year,
                    "trust_score": 10,
                    "retrieval_score": 9.5,
                    "timestamp": timestamp(),
                    "metadata":{
                        "engine":
                        "scholar"
                    }
                })

            except StopIteration:
                break

            except Exception:
                continue

        logger.info(
            f"Scholar Results: "
            f"{len(results)}"
        )
        return results

    except Exception as e:

        logger.error(
            f"Scholar Failed: "
            f"{str(e)}"
        )
        return []

# TAVILY SEARCH

def tavily_search( query: str, deep_mode: bool = True ):

    logger.info(
        f"[{timestamp()}] "
        f"Tavily Search Started: "
        f"{query}"
    )
    try:
        max_results = ( 30 if deep_mode else 10)
        response = tavily.search(
            query=query,
            max_results=max_results,
            include_answer=False,
            include_raw_content=False
        )

        results = []
        for r in response.get( "results",[]):

            url = r.get(  "url", "")

            results.append({
                "id": str(uuid.uuid4()),
                "source": "tavily",
                "title": r.get(
                    "title",
                    ""
                ),
                "url": url,
                "content": r.get("content", "" ),
                "published": r.get(
                    "published_date",
                    "Unknown"
                ),
                "trust_score": get_trust_score( url ),

                "retrieval_score": r.get(  "score", 5),

                "timestamp": timestamp(),

                "metadata": {  "engine": "tavily"}
            })

        logger.info(
            f"Tavily Results: "
            f"{len(results)}"
        )
        return results

    except Exception as e:

        logger.error(
            f"Tavily Failed: "
            f"{str(e)}"
        )
        return []

# ARXIV SEARCH

def arxiv_search(
    query: str,
    limit: int = 20,
    filters: dict = None
):

    logger.info(
        f"[{timestamp()}] "
        f"Arxiv Search: "
        f"{query}"
    )

    try:

        search = arxiv.Search(

            query=query,

            max_results=limit,

            sort_by=(
                arxiv.SortCriterion
                .Relevance
            )
        )

        results = []

        for paper in (
            search.results()
        ):

            year = (
                paper.published.year
            )

            # FILTERS

            if filters:

                year_from = (
                    filters.get(
                        "year_from"
                    )
                )

                if (
                    year_from
                    and year < year_from
                ):
                    continue

            results.append({

                "id":
                str(uuid.uuid4()),

                "source":
                "arxiv",

                "title":
                paper.title,

                "url":
                paper.entry_id,

                "content":
                paper.summary,

                "authors":
                [
                    a.name
                    for a in
                    paper.authors
                ],

                "published":
                str(
                    paper.published
                ),

                "year":
                year,

                "trust_score":
                9,

                "retrieval_score":
                8.7,

                "timestamp":
                timestamp(),

                "metadata":
                {
                    "engine":
                    "arxiv"
                }
            })

        logger.info(
            f"Arxiv Results: "
            f"{len(results)}"
        )

        return results

    except Exception as e:

        logger.error(
            f"Arxiv Failed: "
            f"{str(e)}"
        )

        return []

# PUBMED SEARCH

def pubmed_search(
    query: str,
    limit: int = 20
):

    logger.info(
        f"[{timestamp()}] "
        f"PubMed Search: "
        f"{query}"
    )

    try:

        handle = (
            Entrez.esearch(

                db="pubmed",

                term=query,

                retmax=limit
            )
        )

        record = (
            Entrez.read(
                handle
            )
        )

        ids = record[
            "IdList"
        ]

        results = []

        for pmid in ids:

            results.append({

                "id":
                str(uuid.uuid4()),

                "source":
                "pubmed",

                "title":
                f"PubMed Paper "
                f"{pmid}",

                "url":
                (
                    "https://pubmed.ncbi.nlm.nih.gov/"
                    f"{pmid}/"
                ),

                "content":
                "Medical paper retrieved.",

                "published":
                "Unknown",

                "trust_score":
                10,

                "retrieval_score":
                9,

                "timestamp":
                timestamp(),

                "metadata":
                {
                    "pmid":
                    pmid
                }
            })

        logger.info(
            f"PubMed Results: "
            f"{len(results)}"
        )

        return results

    except Exception as e:

        logger.error(
            f"PubMed Failed: "
            f"{str(e)}"
        )

        return []

# WIKIPEDIA SEARCH

def wiki_search(
    query: str
):

    logger.info(
        f"[{timestamp()}] "
        f"Wikipedia Search: "
        f"{query}"
    )

    try:

        page = wikipedia.page(
            query
        )

        return [{

            "id":
            str(uuid.uuid4()),

            "source":
            "wikipedia",

            "title":
            page.title,

            "url":
            page.url,

            "content":
            page.summary,

            "published":
            "Unknown",

            "trust_score":
            6,

            "retrieval_score":
            6,

            "timestamp":
            timestamp(),

            "metadata":
            {
                "engine":
                "wikipedia"
            }
        }]

    except Exception:

        return []

# FALLBACK SEARCH

def fallback_search(
    query: str
):

    logger.warning(
        "Fallback Search Triggered"
    )

    results = []

    try:

        results.extend(
            wiki_search(query)
        )

    except Exception:
        pass

    try:

        results.extend(
            tavily_search(
                query,
                deep_mode=False
            )
        )

    except Exception:
        pass

    return results


# SOURCE SCORING
def compute_source_score(
    source: dict
):

    trust_score = source.get(
        "trust_score",
        5
    )

    retrieval_score = source.get(
        "retrieval_score",
        5
    )

    citations = source.get(
        "citations",
        0
    )

    year = source.get(
        "year",
        2020
    )

    current_year = (
        time.localtime().tm_year
    )

    # FRESHNESS SCORE

    freshness_score = 5

    try:

        if isinstance(
            year,
            str
        ):

            year = int(year)

        age = (
            current_year
            - year
        )

        if age <= 2:
            freshness_score = 10

        elif age <= 5:
            freshness_score = 8

        elif age <= 10:
            freshness_score = 6

        else:
            freshness_score = 4

    except Exception:
        pass

    # CITATION SCORE

    citation_score = min(
        citations / 100,
        10
    )

    # FINAL WEIGHTED SCORE

    final_score = (

        trust_score * 0.35 +

        retrieval_score * 0.30 +

        freshness_score * 0.15 +

        citation_score * 0.20
    )

    source[
        "freshness_score"
    ] = freshness_score

    source[
        "citation_score"
    ] = citation_score

    source[
        "final_score"
    ] = round(
        final_score,
        2
    )

    return source

# DEDUPLICATION

def deduplicate_results(
    results: List[dict]
):

    logger.info(
        "Deduplicating results..."
    )

    seen_urls = set()

    unique_results = []

    for item in results:

        url = item.get(
            "url",
            ""
        )

        title = item.get(
            "title",
            ""
        )

        unique_key = (
            url
            if url
            else title
        )

        if unique_key not in seen_urls:

            seen_urls.add(
                unique_key
            )

            unique_results.append(
                item
            )

    logger.info(
        f"Dedup Complete | "
        f"{len(results)} "
        f"→ "
        f"{len(unique_results)}"
    )

    return unique_results

# RANKING ENGINE

def rank_results(
    results: List[dict]
):

    logger.info(
        "Ranking results..."
    )

    scored_results = []

    for item in results:

        scored_item = (
            compute_source_score(
                item
            )
        )

        scored_results.append(
            scored_item
        )

    ranked = sorted(

        scored_results,

        key=lambda x:
        x.get(
            "final_score",
            0
        ),

        reverse=True
    )

    logger.info(
        f"Ranking Complete | "
        f"{len(ranked)} "
        f"sources"
    )

    return ranked

# QUERY ROUTER

def route_retrieval(
    query_type: str
):

    logger.info(
        f"Routing Query Type: "
        f"{query_type.upper()}"
    )

    routing_map = {

        "academic": [

            "scholar",
            "arxiv",
            "pubmed",
            "tavily"
        ],

        "technical": [

            "scholar",
            "arxiv",
            "tavily",
            "wiki"
        ],

        "market": [

            "tavily",
            "wiki"
        ],

        "news": [

            "tavily",
            "wiki"
        ]
    }

    return routing_map.get(

        query_type,

        [
            "tavily",
            "wiki"
        ]
    )

# PDF VECTOR STORE

def save_pdf_index():

    global PDF_VECTOR_INDEX
    global PDF_CHUNKS
    global PDF_METADATA

    logger.info(
        "Saving vector DB..."
    )

    faiss.write_index(

        PDF_VECTOR_INDEX,

        os.path.join(
            VECTOR_STORE_DIR,
            "pdf.index"
        )
    )

    with open(

        os.path.join(
            VECTOR_STORE_DIR,
            "chunks.pkl"
        ),

        "wb"

    ) as f:

        pickle.dump(

            PDF_CHUNKS,
            f
        )

    with open(

        os.path.join(
            VECTOR_STORE_DIR,
            "metadata.pkl"
        ),

        "wb"

    ) as f:

        pickle.dump(

            PDF_METADATA,
            f
        )

# LOAD PDF INDEX

def load_pdf_index():

    global PDF_VECTOR_INDEX
    global PDF_CHUNKS
    global PDF_METADATA

    index_path = os.path.join(
        VECTOR_STORE_DIR,
        "pdf.index"
    )

    chunks_path = os.path.join(
        VECTOR_STORE_DIR,
        "chunks.pkl"
    )

    metadata_path = os.path.join(
        VECTOR_STORE_DIR,
        "metadata.pkl"
    )

    if not os.path.exists(
        index_path
    ):
        return False

    logger.info(
        "Loading PDF index..."
    )

    PDF_VECTOR_INDEX = (
        faiss.read_index(
            index_path
        )
    )

    with open(
        chunks_path,
        "rb"
    ) as f:

        PDF_CHUNKS = (
            pickle.load(f)
        )

    with open(
        metadata_path,
        "rb"
    ) as f:

        PDF_METADATA = (
            pickle.load(f)
        )

    logger.info(
        "PDF Index Loaded"
    )

    return True

# ADD PDFS TO VECTOR DB

def ingest_pdfs(
    pdf_paths: List[str]
):

    global PDF_VECTOR_INDEX
    global PDF_CHUNKS
    global PDF_METADATA

    logger.info(
        f"PDF Ingestion Started "
        f"| Files={len(pdf_paths)}"
    )

    all_chunks = []
    all_metadata = []

    for path in pdf_paths:

        logger.info(
            f"Processing PDF: "
            f"{path}"
        )

        text = extract_pdf_text(
            path
        )

        if not text:
            continue

        chunks = chunk_text(
            text
        )

        metadata = [

            {
                "source":
                os.path.basename(
                    path
                ),

                "chunk_id":
                i
            }

            for i in range(
                len(chunks)
            )
        ]

        all_chunks.extend(
            chunks
        )

        all_metadata.extend(
            metadata
        )

    if not all_chunks:

        logger.warning(
            "No valid PDF chunks."
        )

        return False

    embeddings = (
        embed_chunks(
            all_chunks
        )
    )

    PDF_VECTOR_INDEX = (
        build_faiss_index(
            embeddings
        )
    )

    PDF_CHUNKS = (
        all_chunks
    )

    PDF_METADATA = (
        all_metadata
    )

    save_pdf_index()

    logger.info(
        f"PDF Ingestion Complete "
        f"| Chunks={len(all_chunks)}"
    )

    return True

# PDF SEMANTIC SEARCH

def retrieve_pdf_context(
    query: str,
    top_k: int = 10
):

    global PDF_VECTOR_INDEX

    if PDF_VECTOR_INDEX is None:

        loaded = (
            load_pdf_index()
        )

        if not loaded:

            return []

    logger.info(
        f"PDF Search: {query}"
    )

    query_embedding = (
        embedding_model.encode(
            [query]
        )
    )

    query_embedding = np.array(

        query_embedding,

        dtype=np.float32
    )

    distances, indices = (

        PDF_VECTOR_INDEX.search(

            query_embedding,

            top_k
        )
    )

    results = []

    for idx in indices[0]:

        if idx >= len(
            PDF_CHUNKS
        ):
            continue

        results.append({

            "source":
            "pdf",

            "title":
            PDF_METADATA[idx][
                "source"
            ],

            "content":
            PDF_CHUNKS[idx],

            "trust_score":
            9,

            "retrieval_score":
            8.5,

            "metadata":
            PDF_METADATA[idx]
        })

    logger.info(
        f"PDF Retrieved: "
        f"{len(results)}"
    )

    return results

# DEEP MULTI-RETRIEVAL

def run_multi_retrieval(

    query: str,

    mode: str = "research",

    filters: dict = None
):

    start_time = time.time()

    logger.info(
        "=" * 50
    )

    logger.info(
        f"STARTING DEEP RETRIEVAL"
    )

    logger.info(
        f"Query: {query}"
    )

    logger.info(
        f"Mode: {mode}"
    )

    query_type = (
        detect_query_type(
            query
        )
    )

    config = (
        get_mode_config(
            mode
        )
    )

    retrieval_engines = (
        route_retrieval(
            query_type
        )
    )

    all_results = []

    # GOOGLE SCHOLAR

    if "scholar" in retrieval_engines:

        scholar_results = (

            google_scholar_search(

                query=query,

                limit=config[
                    "scholar_limit"
                ],

                filters=filters
            )
        )

        all_results.extend(
            scholar_results
        )

    # ARXIV

    if "arxiv" in retrieval_engines:

        arxiv_results = (

            arxiv_search(

                query=query,

                limit=config[
                    "arxiv_limit"
                ],

                filters=filters
            )
        )

        all_results.extend(
            arxiv_results
        )

    # PUBMED

    if "pubmed" in retrieval_engines:

        pubmed_results = (

            pubmed_search(

                query=query,

                limit=config[
                    "pubmed_limit"
                ]
            )
        )

        all_results.extend(
            pubmed_results
        )

    # TAVILY

    if "tavily" in retrieval_engines:

        tavily_results = (

            tavily_search(

                query=query,

                deep_mode=config[
                    "deep_mode"
                ]
            )
        )

        all_results.extend(
            tavily_results
        )

    # WIKIPEDIA

    if "wiki" in retrieval_engines:

        wiki_results = (
            wiki_search(
                query
            )
        )

        all_results.extend(
            wiki_results
        )

    # PDF SEARCH

    pdf_results = (
        retrieve_pdf_context(
            query
        )
    )

    all_results.extend(
        pdf_results
    )

    # FALLBACK

    if len(
        all_results
    ) < 5:

        logger.warning(
            "Low retrieval count "
            "→ fallback search"
        )

        fallback_results = (

            fallback_search(
                query
            )
        )

        all_results.extend(
            fallback_results
        )

    # CLEAN + RANK

    deduped = (
        deduplicate_results(
            all_results
        )
    )

    ranked = (
        rank_results(
            deduped
        )
    )

    ranked = ranked[
        :config[
            "max_sources"
        ]
    ]

    latency = round(

        time.time()
        - start_time,

        2
    )

    logger.info(
        f"Retrieval Complete "
        f"| Sources="
        f"{len(ranked)} "
        f"| Latency="
        f"{latency}s"
    )

    logger.info(
        "=" * 50
    )

    return ranked

# WEB SEARCH TOOL
@tool
def web_Search(
    query: str,
    mode: str = "research",
    filters: dict = None
):
    """
    Deep research web search.

    Supports:
    - Quick mode
    - Research mode
    - Deep mode

    Sources:
    - Google Scholar
    - Tavily
    - Arxiv
    - PubMed
    - Wikipedia
    - Uploaded PDFs

    Returns:
    ranked evidence-grounded sources
    """

    try:

        logger.info(
            "=" * 60
        )

        logger.info(
            f"[{timestamp()}] "
            f"WEB SEARCH STARTED"
        )

        logger.info(
            f"Query: {query}"
        )

        logger.info(
            f"Mode: {mode}"
        )

        if filters:

            logger.info(
                f"Filters: "
                f"{filters}"
            )

        results = (
            run_multi_retrieval(

                query=query,

                mode=mode,

                filters=filters
            )
        )

        if not results:

            logger.warning(
                "No retrieval results."
            )

            return []

        logger.info(
            f"Retrieved "
            f"{len(results)} "
            f"sources"
        )

        logger.info(
            "=" * 60
        )

        return results

    except Exception as e:

        logger.error(
            f"web_Search failed: "
            f"{str(e)}"
        )

        return []

# SCRAPE URL

@tool
def scrape_url(
    url: str
):

    """
    Scrape webpage content
    with cleaning,
    timeout handling,
    retries,
    and trust metadata.
    """

    logger.info(
        f"[{timestamp()}] "
        f"Scraping URL:"
    )

    logger.info(url)

    try:

        headers = {

            "User-Agent":

            (
                "Mozilla/5.0 "
                "(Macintosh; "
                "Intel Mac OS X)"
            )
        }

        response = requests.get(

            url,

            timeout=20,

            headers=headers
        )

        response.raise_for_status()

        soup = BeautifulSoup(

            response.text,

            "html.parser"
        )

        # REMOVE NOISE

        noisy_tags = [

            "script",
            "style",
            "nav",
            "footer",
            "header",
            "iframe",
            "noscript",
            "svg",
            "form",
            "button",
            "aside"
        ]

        for tag in soup(
            noisy_tags
        ):

            tag.decompose()

        content = soup.get_text(

            separator=" ",

            strip=True
        )

        # CLEAN WHITESPACE

        content = re.sub(

            r"\s+",

            " ",

            content
        )

        # SHORT CONTENT FAIL

        if len(content) < 150:

            logger.warning(
                "Insufficient "
                "page content."
            )

            return {

                "url": url,
                "status": "failed",
                "content": "",
                "trust_score":
                get_trust_score(url),
                "reason": "Low content"
            }

        cleaned_content = (content[:4000])

        logger.info(
            f"Scrape Success | "
            f"Chars="
            f"{len(cleaned_content)}"
        )

        return {
            "url": url,
            "status": "success",
            "content": cleaned_content,
            "trust_score": get_trust_score( url ),
            "timestamp": timestamp()
        }

    except requests.exceptions.Timeout:
        logger.error("Scrape Timeout")
        return {
            "url": url,
            "status": "failed",
            "content": "",
            "reason": "timeout"
        }

    except requests.exceptions.ConnectionError:
        logger.error( "Connection Error" )
        return {
            "url": url,
            "status": "failed",
            "content": "",
            "reason": "connection_error"
        }

    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTP Error: "
            f"{str(e)}"
        )
        return {
            "url": url,
            "status": "failed",
            "content": "",
            "reason": str(e)
        }

    except Exception as e:
        logger.error(
            f"Scraping Failed: "
            f"{str(e)}"
        )

        return {
            "url": url,
            "status": "failed",
            "content": "",
            "reason": str(e)
        }

# TESTING

if __name__ == "__main__":

    print("\n")
    print("=" * 70)
    print("RESEARCH ENGINE TEST")
    print("=" * 70)

    query = ( "Future of Quantum Security")

    results = web_Search.invoke({
        "query": query,
        "mode": "deep",
        "filters": {
            "year_from": 2018,
            "min_citations": 20
        }
    })

    print("\n")
    print(
        f"Retrieved: "
        f"{len(results)} "
        f"sources"
    )

    print("\nTOP RESULTS:\n")

    for idx, item in enumerate(
        results[:10],
        start=1
    ):

        print(
            f"{idx}. "
            f"{item.get('title')}"
        )

        print(
            f"Source: "
            f"{item.get('source')}"
        )

        print(
            f"Trust Score: "
            f"{item.get('trust_score')}"
        )

        print(
            f"Final Score: "
            f"{item.get('final_score')}"
        )

        print(
            f"URL: "
            f"{item.get('url')}"
        )
        print("-" * 50)

    print("\n")
    print("=" * 70)
    print("SCRAPE TEST")
    print("=" * 70)

    scraped = scrape_url.invoke({ "url": "https://www.nature.com" })
    print("\n")
    print( scraped.get("status") )
    print(scraped.get( "content", "")[:500])