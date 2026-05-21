import os
import re
import time
import json
import queue
import logging
import requests
import wikipedia
import arxiv
import warnings

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

from langchain.tools import tool

warnings.filterwarnings("ignore")

# ENVIRONMENT

load_dotenv()

TAVILY_API_KEY = os.getenv(
    "TAVILY_API_KEY"
)

if not TAVILY_API_KEY:
    raise ValueError(
        "TAVILY_API_KEY missing "
        "in .env"
    )

PUBMED_EMAIL = os.getenv(
    "PUBMED_EMAIL",
    "researchengine@gmail.com"
)

Entrez.email = PUBMED_EMAIL

tavily = TavilyClient(
    api_key=TAVILY_API_KEY
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
    "ResearchEngine"
)

# QUERY TYPES

ACADEMIC_KEYWORDS = [

    "research",
    "paper",
    "study",
    "journal",
    "scientific",
    "academic",
    "cryptography",
    "security",
    "quantum",
    "ai",
    "machine learning",
    "deep learning",
    "biology",
    "physics",
    "chemistry",
    "medicine",
    "healthcare",
    "neural networks",
    "computer vision",
    "nlp",
    "genomics"
]

NEWS_KEYWORDS = [

    "latest",
    "today",
    "breaking",
    "news",
    "recent",
    "update",
    "announced",
    "this week",
    "current"
]

MARKET_KEYWORDS = [

    "market",
    "stocks",
    "industry",
    "forecast",
    "investment",
    "valuation",
    "startup",
    "business",
    "economy",
    "competition"
]

TECHNICAL_KEYWORDS = [

    "architecture",
    "system",
    "design",
    "framework",
    "api",
    "engineering",
    "database",
    "distributed systems",
    "compiler",
    "firmware"
]

# TRUSTED SOURCE REGISTRY (100+)

TRUSTED_DOMAINS = {

    # GOVERNMENT

    ".gov": 10,
    "whitehouse.gov": 10,
    "nist.gov": 10,
    "nih.gov": 10,
    "nsf.gov": 10,
    "nasa.gov": 10,
    "darpa.mil": 10,
    "energy.gov": 10,
    "epa.gov": 10,
    "sec.gov": 10,
    "treasury.gov": 10,
    "fda.gov": 10,
    "cdc.gov": 10,
    "europa.eu": 10,
    "gov.uk": 10,
    "oecd.org": 10,
    "worldbank.org": 10,
    "imf.org": 10,
    "who.int": 10,
    "un.org": 10,
    "wipo.int": 10,
    "uspto.gov": 10,

    # UNIVERSITIES

    ".edu": 9,
    "mit.edu": 10,
    "stanford.edu": 10,
    "harvard.edu": 10,
    "berkeley.edu": 10,
    "cmu.edu": 10,
    "princeton.edu": 10,
    "caltech.edu": 10,
    "cornell.edu": 10,
    "yale.edu": 10,
    "columbia.edu": 10,
    "upenn.edu": 10,
    "ucla.edu": 10,
    "uchicago.edu": 10,
    "ox.ac.uk": 10,
    "cam.ac.uk": 10,
    "imperial.ac.uk": 10,
    "ethz.ch": 10,

    # PAPERS / JOURNALS

    "nature.com": 10,
    "science.org": 10,
    "ieee.org": 10,
    "acm.org": 10,
    "springer.com": 9,
    "springernature.com": 9,
    "sciencedirect.com": 9,
    "arxiv.org": 9,
    "pubmed.ncbi.nlm.nih.gov": 10,
    "ncbi.nlm.nih.gov": 10,
    "semanticscholar.org": 9,
    "jstor.org": 9,
    "wiley.com": 8,
    "frontiersin.org": 8,
    "plos.org": 8,
    "ssrn.com": 8,
    "researchgate.net": 7,
    "mdpi.com": 7,
    "tandfonline.com": 8,

    # AI RESEARCH LABS

    "openai.com": 9,
    "deepmind.google": 9,
    "anthropic.com": 9,
    "ai.meta.com": 9,
    "research.google": 9,
    "microsoft.com/research": 9,
    "ibm.com/research": 9,
    "nvidia.com/research": 9,
    "allenai.org": 9,
    "huggingface.co": 8,

    # MARKET RESEARCH

    "gartner.com": 9,
    "mckinsey.com": 9,
    "bain.com": 9,
    "bcg.com": 9,
    "forrester.com": 9,
    "cbinsights.com": 8,
    "pitchbook.com": 8,
    "statista.com": 8,
    "goldmansachs.com": 8,
    "morganstanley.com": 8,
    "bloomberg.com": 8,

    # BUSINESS

    "wsj.com": 8,
    "ft.com": 8,
    "economist.com": 8,
    "forbes.com": 7,
    "fortune.com": 7,
    "hbr.org": 8,
    "marketwatch.com": 7,
    "ycombinator.com": 8,

    # NEWS

    "reuters.com": 9,
    "apnews.com": 9,
    "bbc.com": 8,
    "nytimes.com": 8,
    "washingtonpost.com": 8,
    "theguardian.com": 8,
    "cnbc.com": 8,
    "techcrunch.com": 7,
    "theverge.com": 7,

    # TECHNICAL DOCS

    "developer.nvidia.com": 8,
    "developer.apple.com": 8,
    "learn.microsoft.com": 8,
    "aws.amazon.com": 8,
    "cloud.google.com": 8,
    "docs.python.org": 8,
    "kubernetes.io": 8,
    "developer.mozilla.org": 8,
    "react.dev": 8,
    "nodejs.org": 8,

    # MEDICAL

    "mayoclinic.org": 9,
    "clevelandclinic.org": 9,
    "webmd.com": 6,
}

# RETRY CONFIG

MAX_RETRIES = 3
REQUEST_TIMEOUT = 20
DEEP_MODE_RESULTS = 30
NORMAL_MODE_RESULTS = 10

# HELPERS

def detect_query_type(query: str):

    query_lower = query.lower()

    academic_score = sum(
        1 for k in
        ACADEMIC_KEYWORDS
        if k in query_lower
    )

    news_score = sum(
        1 for k in
        NEWS_KEYWORDS
        if k in query_lower
    )

    market_score = sum(
        1 for k in
        MARKET_KEYWORDS
        if k in query_lower
    )

    technical_score = sum(
        1 for k in
        TECHNICAL_KEYWORDS
        if k in query_lower
    )

    scores = {

        "academic":
        academic_score,

        "news":
        news_score,

        "market":
        market_score,

        "technical":
        technical_score
    }

    detected = max(
        scores,
        key=scores.get
    )

    logger.info(
        f"Query Type: "
        f"{detected.upper()}"
    )

    return detected


def get_trust_score(url):

    url = url.lower()

    for domain, score in (
        TRUSTED_DOMAINS.items()
    ):

        if domain in url:

            return score

    return 5


def timestamp():

    return time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# TAVILY SEARCH

@retry(
    stop=stop_after_attempt(
        MAX_RETRIES
    ),
    wait=wait_exponential(
        multiplier=2
    )
)
def tavily_search(
    query,
    deep_mode=True
):

    try:

        logger.info(
            f"[{timestamp()}] "
            f"Tavily Search "
            f"Started: {query}"
        )

        max_results = (
            DEEP_MODE_RESULTS
            if deep_mode
            else NORMAL_MODE_RESULTS
        )

        response = tavily.search(

            query=query,

            max_results=max_results,

            include_answer=False,

            include_raw_content=False
        )

        results = []

        for r in response.get(
            "results", []
        ):

            url = r.get(
                "url", ""
            )

            results.append({

                "source":
                "tavily",

                "title":
                r.get(
                    "title", ""
                ),

                "url":
                url,

                "content":
                r.get(
                    "content", ""
                ),

                "published":
                r.get(
                    "published_date",
                    "Unknown"
                ),

                "trust_score":
                get_trust_score(
                    url
                ),

                "retrieval_score":
                r.get(
                    "score",
                    0
                ),

                "timestamp":
                timestamp(),

                "metadata":
                {
                    "engine":
                    "tavily"
                }
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


# GOOGLE SCHOLAR
def google_scholar_search(
    query,
    limit=20
):

    try:

        logger.info(
            f"[{timestamp()}] "
            f"Scholar Search: "
            f"{query}"
        )

        search_query = (
            scholarly.search_pubs(
                query
            )
        )

        papers = []

        for _ in range(limit):

            try:

                paper = next(
                    search_query
                )

                bib = paper.get(
                    "bib",
                    {}
                )

                papers.append({

                    "source":
                    "google_scholar",

                    "title":
                    bib.get(
                        "title", ""
                    ),

                    "url":
                    paper.get(
                        "pub_url",
                        ""
                    ),

                    "content":
                    bib.get(
                        "abstract",
                        ""
                    ),

                    "authors":
                    bib.get(
                        "author",
                        []
                    ),

                    "year":
                    bib.get(
                        "pub_year",
                        "Unknown"
                    ),

                    "citations":
                    paper.get(
                        "num_citations",
                        0
                    ),

                    "trust_score":
                    10,

                    "retrieval_score":
                    9,

                    "timestamp":
                    timestamp(),

                    "metadata":
                    {
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
            f"{len(papers)}"
        )

        return papers

    except Exception as e:

        logger.error(
            f"Scholar Failed: "
            f"{str(e)}"
        )

        return []


# ARXIV

def arxiv_search(
    query,
    limit=20
):

    try:

        logger.info(
            f"[{timestamp()}] "
            f"Arxiv Search: "
            f"{query}"
        )

        search = arxiv.Search(

            query=query,

            max_results=limit,

            sort_by=(
                arxiv.SortCriterion
                .Relevance
            )
        )

        papers = []

        for paper in (
            search.results()
        ):

            papers.append({

                "source":
                "arxiv",

                "title":
                paper.title,

                "url":
                paper.entry_id,

                "content":
                paper.summary,

                "published":
                str(
                    paper.published
                ),

                "authors":
                [
                    a.name
                    for a in
                    paper.authors
                ],

                "trust_score":
                9,

                "retrieval_score":
                8.5,

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
            f"{len(papers)}"
        )

        return papers

    except Exception as e:

        logger.error(
            f"Arxiv Failed: "
            f"{str(e)}"
        )

        return []


# PUBMED

def pubmed_search(
    query,
    limit=20
):

    try:

        logger.info(
            f"[{timestamp()}] "
            f"PubMed Search: "
            f"{query}"
        )

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

        papers = []

        for pmid in ids:

            papers.append({

                "source":
                "pubmed",

                "title":
                f"PubMed {pmid}",

                "url":
                (
                    "https://pubmed.ncbi.nlm.nih.gov/"
                    f"{pmid}/"
                ),

                "content":
                "Medical research paper",

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
            f"{len(papers)}"
        )

        return papers

    except Exception as e:

        logger.error(
            f"PubMed Failed: "
            f"{str(e)}"
        )

        return []


# WIKIPEDIA

def wiki_search(
    query
):

    try:

        logger.info(
            f"[{timestamp()}] "
            f"Wikipedia Search: "
            f"{query}"
        )

        page = wikipedia.page(
            query
        )

        return [{

            "source":
            "wikipedia",

            "title":
            page.title,

            "url":
            page.url,

            "content":
            page.summary,

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
    


# SOURCE SCORING ENGINE

def compute_freshness_score(
    published
):

    try:

        if (
            not published
            or published
            == "Unknown"
        ):

            return 5

        current_year = (
            time.localtime()
            .tm_year
        )

        year_match = re.search(
            r"\d{4}",
            str(published)
        )

        if not year_match:
            return 5

        year = int(
            year_match.group()
        )

        age = (
            current_year
            - year
        )

        if age <= 1:
            return 10

        elif age <= 3:
            return 9

        elif age <= 5:
            return 8

        elif age <= 10:
            return 7

        elif age <= 20:
            return 6

        else:
            return 4

    except Exception:

        return 5


def compute_authority_score(
    source
):

    source = (
        source.lower()
    )

    authority_map = {

        "google_scholar":
        10,

        "pubmed":
        10,

        "arxiv":
        9,

        "tavily":
        8,

        "wikipedia":
        5
    }

    return authority_map.get(
        source,
        5
    )


def compute_citation_score(
    item
):

    citations = item.get(
        "citations",
        0
    )

    if citations >= 500:
        return 10

    elif citations >= 200:
        return 9

    elif citations >= 100:
        return 8

    elif citations >= 50:
        return 7

    elif citations >= 20:
        return 6

    elif citations >= 5:
        return 5

    return 3


def compute_content_quality(
    content
):

    if not content:
        return 2

    length = len(content)

    if length > 4000:
        return 10

    elif length > 2500:
        return 9

    elif length > 1500:
        return 8

    elif length > 800:
        return 7

    elif length > 400:
        return 5

    return 3


def score_source(
    item
):

    trust_score = item.get(
        "trust_score",
        5
    )

    retrieval_score = (
        item.get(
            "retrieval_score",
            5
        )
    )

    freshness_score = (
        compute_freshness_score(
            item.get(
                "published",
                "Unknown"
            )
        )
    )

    authority_score = (
        compute_authority_score(
            item.get(
                "source",
                ""
            )
        )
    )

    citation_score = (
        compute_citation_score(
            item
        )
    )

    content_score = (
        compute_content_quality(
            item.get(
                "content",
                ""
            )
        )
    )

    final_score = round(

        (

            trust_score * 0.25

            +

            authority_score
            * 0.20

            +

            freshness_score
            * 0.10

            +

            retrieval_score
            * 0.20

            +

            citation_score
            * 0.10

            +

            content_score
            * 0.15

        ),

        2
    )

    item[
        "freshness_score"
    ] = freshness_score

    item[
        "authority_score"
    ] = authority_score

    item[
        "citation_score"
    ] = citation_score

    item[
        "content_score"
    ] = content_score

    item[
        "final_score"
    ] = final_score

    return item


# DUPLICATE REMOVAL

def deduplicate_sources(
    results
):

    seen_urls = set()

    unique_results = []

    for item in results:

        url = item.get(
            "url",
            ""
        )

        normalized_url = (
            url
            .strip()
            .lower()
        )

        if (
            normalized_url
            and normalized_url
            not in seen_urls
        ):

            seen_urls.add(
                normalized_url
            )

            unique_results.append(
                item
            )

    logger.info(

        f"Deduplication: "

        f"{len(results)}"

        f" → "

        f"{len(unique_results)}"
    )

    return unique_results


# SOURCE RANKING

def rank_sources(
    results
):

    logger.info(
        "Ranking Sources..."
    )

    scored_results = []

    for item in results:

        try:

            scored = (
                score_source(
                    item
                )
            )

            scored_results.append(
                scored
            )

        except Exception:

            continue

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

        f"Top Ranked Source: "

        f"{ranked[0]['title']}"

        if ranked
        else

        "No ranked results"
    )

    return ranked


# SMART ROUTING ENGINE

def smart_route_query(
    query,
    deep_mode=True
):

    logger.info(
        f"Routing Query: "
        f"{query}"
    )

    query_type = (
        detect_query_type(
            query
        )
    )

    sources = {

        "tavily": True,

        "scholar": False,

        "arxiv": False,

        "pubmed": False,

        "wiki": True
    }

    # ACADEMIC

    if (
        query_type
        == "academic"
    ):

        sources[
            "scholar"
        ] = True

        sources[
            "arxiv"
        ] = True

        sources[
            "pubmed"
        ] = True

    # TECHNICAL

    elif (
        query_type
        == "technical"
    ):

        sources[
            "scholar"
        ] = True

        sources[
            "arxiv"
        ] = True

    # MARKET

    elif (
        query_type
        == "market"
    ):

        sources[
            "scholar"
        ] = True

    # NEWS

    elif (
        query_type
        == "news"
    ):

        sources[
            "wiki"
        ] = False

    logger.info(

        f"Routing Plan: "

        f"{sources}"
    )

    return sources

# MAIN SEARCH TOOL

@tool
def web_Search(
    query: str,
    deep_mode: bool = True
):

    """
    Deep multi-source retrieval engine.

    Returns:
    ranked evidence-backed sources
    """

    start_time = time.time()

    logger.info(

        "\n"

        + "=" * 60 +

        f"\nSTARTING DEEP SEARCH\n"

        f"Query: {query}\n"

        + "=" * 60
    )

    try:

        # ROUTING

        routing_plan = (
            smart_route_query(
                query=query,
                deep_mode=deep_mode
            )
        )

        logger.info(
            f"Routing Selected: "
            f"{routing_plan}"
        )

        all_results = []

        # TAVILY

        if routing_plan.get(
            "tavily"
        ):

            logger.info(
                "\nRunning Tavily..."
            )

            tavily_results = (
                tavily_search(
                    query=query,
                    deep_mode=deep_mode
                )
            )

            logger.info(
                f"Tavily Retrieved: "
                f"{len(tavily_results)}"
            )

            all_results.extend(
                tavily_results
            )

        # GOOGLE SCHOLAR

        if routing_plan.get(
            "scholar"
        ):

            logger.info(
                "\nRunning Scholar..."
            )

            scholar_results = (
                google_scholar_search(
                    query=query,

                    limit=(
                        35
                        if deep_mode
                        else 15
                    )
                )
            )

            logger.info(
                f"Scholar Retrieved: "
                f"{len(scholar_results)}"
            )

            all_results.extend(
                scholar_results
            )

        # ARXIV

        if routing_plan.get(
            "arxiv"
        ):

            logger.info(
                "\nRunning Arxiv..."
            )

            arxiv_results = (
                arxiv_search(

                    query=query,

                    limit=(
                        30
                        if deep_mode
                        else 10
                    )
                )
            )

            logger.info(
                f"Arxiv Retrieved: "
                f"{len(arxiv_results)}"
            )

            all_results.extend(
                arxiv_results
            )

        # PUBMED

        if routing_plan.get(
            "pubmed"
        ):

            logger.info(
                "\nRunning PubMed..."
            )

            pubmed_results = (
                pubmed_search(

                    query=query,

                    limit=(
                        25
                        if deep_mode
                        else 10
                    )
                )
            )

            logger.info(
                f"PubMed Retrieved: "
                f"{len(pubmed_results)}"
            )

            all_results.extend(
                pubmed_results
            )

        # WIKIPEDIA

        if routing_plan.get(
            "wiki"
        ):

            logger.info(
                "\nRunning Wiki..."
            )

            wiki_results = (
                wiki_search(
                    query
                )
            )

            logger.info(
                f"Wiki Retrieved: "
                f"{len(wiki_results)}"
            )

            all_results.extend(
                wiki_results
            )

        # EMPTY FALLBACK

        if not all_results:

            logger.warning(
                "No sources retrieved."
            )

            return []

        # DEDUPLICATION

        logger.info(
            "\nDeduplicating..."
        )

        deduped_results = (
            deduplicate_sources(
                all_results
            )
        )

        # RANKING

        logger.info(
            "\nRanking Sources..."
        )

        ranked_results = (
            rank_sources(
                deduped_results
            )
        )

        # LIMIT OUTPUT

        final_results = (
            ranked_results[
                :120
            ]
            if deep_mode
            else
            ranked_results[
                :40
            ]
        )

        # OBSERVABILITY

        total_time = round(

            time.time()
            - start_time,

            2
        )

        logger.info(

            "\n"

            + "=" * 60 +

            f"\nSEARCH COMPLETE\n"

            f"Topic: {query}\n"

            f"Total Sources: "
            f"{len(final_results)}\n"

            f"Execution Time: "
            f"{total_time}s\n"

            + "=" * 60
        )

        # PRINT TOP SOURCES

        print("\nTOP SOURCES\n")

        for idx, item in enumerate(

            final_results[:20],

            start=1
        ):

            print(

                f"{idx}. "

                f"[{item.get('source')}] "

                f"{item.get('title')}"

            )

            print(

                f"URL: "

                f"{item.get('url')}"

            )

            print(

                f"Score: "

                f"{item.get('final_score')}"

            )

            print("-" * 50)

        return final_results

    except Exception as e:

        logger.error(

            f"Search Failed: "

            f"{str(e)}"
        )

        return []


# SCRAPER TOOL

@tool
def scrape_url(
    url: str
):

    """
    Scrape webpage content
    for evidence extraction.
    """

    try:

        logger.info(
            f"Scraping URL: "
            f"{url}"
        )

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

            headers=headers,

            timeout=20
        )

        response.raise_for_status()

        soup = BeautifulSoup(

            response.text,

            "html.parser"
        )

        # REMOVE NOISE

        remove_tags = [

            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "noscript",
            "svg",
            "iframe",
            "form",
            "button"
        ]

        for tag in soup(
            remove_tags
        ):

            tag.decompose()

        # CLEAN TEXT

        text = soup.get_text(

            separator=" ",

            strip=True
        )

        text = re.sub(

            r"\s+",

            " ",

            text
        )

        # QUALITY CHECK

        if len(text) < 200:

            logger.warning(
                "Low content page."
            )

            return ""

        logger.info(

            f"Scrape Success | "

            f"Chars: "

            f"{len(text)}"
        )

        return text[:12000]

    except requests.Timeout:

        logger.error(
            "Scrape Timeout"
        )

        return ""

    except Exception as e:

        logger.error(

            f"Scrape Failed: "

            f"{str(e)}"
        )

        return ""


# LOCAL TESTING

if __name__ == "__main__":

    topic = (
        "Future of Quantum Security"
    )

    results = (
        web_Search.invoke({

            "query":
            topic,

            "deep_mode":
            True
        })
    )

    print(
        "\nRetrieved:",
        len(results)
    )

    if results:

        print("\nTOP RESULT\n")

        print(
            json.dumps(

                results[0],

                indent=2,

                default=str
            )
        )


# planner
# deep retrieval
# ranking
# top evidence scrape
# deep synthesis
# critic
# observability
# No  search_agent dependency anymore.
