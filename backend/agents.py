
import os
import json
import time
import logging
import warnings

from typing import (
    Dict,
    Any
)

from dotenv import (
    load_dotenv
)

from langchain_mistralai import (
    ChatMistralAI
)

from langchain_core.prompts import (
    ChatPromptTemplate
)

from langchain_core.output_parsers import (

    JsonOutputParser,

    StrOutputParser
)

# CONFIG

warnings.filterwarnings(
    "ignore"
)

load_dotenv()

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
    "research_agents"
)

# ENV CONFIG

MISTRAL_API_KEY = os.getenv(
    "MISTRAL_API_KEY"
)

if not MISTRAL_API_KEY:

    raise ValueError(
        "MISTRAL_API_KEY "
        "missing in .env"
    )

# MODEL CONFIG

FAST_MODEL = os.getenv(

    "FAST_MODEL",

    "mistral-small-latest"
)

REASONING_MODEL = os.getenv(

    "REASONING_MODEL",

    "mistral-small-latest"
)

CRITIC_MODEL = os.getenv(

    "CRITIC_MODEL",

    "mistral-small-latest"
)

TEMPERATURE = float(

    os.getenv(

        "TEMPERATURE",

        "0.2"
    )
)

TIMEOUT = int(

    os.getenv(

        "TIMEOUT",

        "180"
    )
)

MAX_RETRIES = int(

    os.getenv(

        "MAX_RETRIES",

        "3"
    )
)

# MULTI MODEL SETUP

fast_llm = ChatMistralAI(

    model=FAST_MODEL,

    api_key=
    MISTRAL_API_KEY,

    temperature=0.1,

    timeout=120,

    max_retries=3
)

reasoning_llm = ChatMistralAI(

    model=
    REASONING_MODEL,

    api_key=
    MISTRAL_API_KEY,

    temperature=0.2,

    timeout=240,

    max_retries=4
)

critic_llm = ChatMistralAI(

    model=
    CRITIC_MODEL,

    api_key=
    MISTRAL_API_KEY,

    temperature=0.1,

    timeout=180,

    max_retries=4
)

# QUERY COMPLEXITY

class QueryComplexityEstimator:

    @staticmethod
    def estimate(
        query: str
    ) -> Dict[str, Any]:

        query_lower = (
            query.lower()
        )

        deep_keywords = [

            "deep research",
            "history",
            "analysis",
            "technical",
            "architecture",
            "compare",
            "future",
            "forecast",
            "evidence",
            "research paper",
            "benchmark",
            "whitepaper",
            "academic",
            "scholar",
            "40 years",
            "industry",
            "contradiction",
            "scientific"
        ]

        academic_keywords = [

            "paper",
            "journal",
            "citation",
            "study",
            "pubmed",
            "arxiv",
            "nature",
            "ieee",
            "research"
        ]

        news_keywords = [

            "today",
            "latest",
            "breaking",
            "recent",
            "news"
        ]

        score = 0

        # KEYWORD SCORE
        for word in (
            deep_keywords
        ):

            if word in (
                query_lower
            ):

                score += 2

        # QUERY LENGTH

        query_length = len(
            query.split()
        )

        score += min(
            query_length // 5,
            4
        )

        # COMPLEXITY

        if score <= 3:

            complexity = (
                "low"
            )

        elif score <= 8:

            complexity = (
                "medium"
            )

        else:

            complexity = (
                "high"
            )

        # QUERY TYPE

        query_type = (
            "general"
        )

        if any(

            word in
            query_lower

            for word in
            academic_keywords
        ):

            query_type = (
                "academic"
            )

        elif any(

            word in
            query_lower

            for word in
            news_keywords
        ):

            query_type = (
                "news"
            )

        # SOURCE COUNT

        estimated_sources = (

            20
            if complexity
            == "low"

            else 60
            if complexity
            == "medium"

            else 150
        )

        return {

            "complexity":
            complexity,

            "query_type":
            query_type,

            "score":
            score,

            "estimated_sources":
            estimated_sources
        }

# MODEL ROUTER

class ModelRouter:

    @staticmethod
    def route(
        complexity: str
    ):

        if complexity == "low":

            logger.info(
                "Using "
                "FAST MODEL"
            )

            return fast_llm

        elif (
            complexity
            == "medium"
        ):

            logger.info(
                "Using "
                "REASONING MODEL"
            )

            return reasoning_llm

        logger.info(
            "Using "
            "CRITIC MODEL"
        )

        return critic_llm

# QUERY PLANNER PROMPT

planner_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a
world-class
research planner.

You MUST:

1. understand intent
2. decompose query
3. generate subqueries
4. extract entities
5. choose sources
6. decide retrieval

Return ONLY JSON.

FORMAT:

{{
 "main_query": "",
 "intent": "",
 "complexity": "",
 "query_type": "",
 "time_horizon": "",
 "search_depth": "",
 "subqueries": [],
 "entities": [],
 "source_types": [],
 "retrieval_strategy": "",
 "reasoning_type": "",
 "priority_order": []
}}

Rules:

Simple query:
1–2 subqueries

Medium:
3–4 subqueries

Deep research:
5–8 subqueries

Prefer
research-quality
queries.
"""
        ),

        (
            "human",

            """
Research Query:

{query}
"""
        )
    ])
)

query_planner_chain = (

    planner_prompt

    | fast_llm

    | JsonOutputParser()
)

# SAFE PLANNER
# JSON FAILURE RECOVERY

def safe_planner(
    query: str
):

    try:

        logger.info(
            "Planner Started"
        )

        result = (
            query_planner_chain
            .invoke({

                "query":
                query
            })
        )

        logger.info(
            "Planner Success"
        )

        return result

    except Exception as e:

        logger.warning(
            f"Planner Failed: "
            f"{str(e)}"
        )

        return {

            "main_query":
            query,

            "intent":
            "technical",

            "complexity":
            "medium",

            "query_type":
            "general",

            "time_horizon":
            "current",

            "search_depth":
            "medium",

            "subqueries": [

                query
            ],

            "entities": [],

            "source_types": [

                "scholar",

                "web"
            ],

            "retrieval_strategy":
            "hybrid",

            "reasoning_type":
            "technical",

            "priority_order": [

                "scholar",

                "web"
            ]
        }

# RESEARCH MODE

def get_research_mode(
    query: str
):

    analysis = (
        QueryComplexityEstimator
        .estimate(query)
    )

    llm = (
        ModelRouter.route(

            analysis[
                "complexity"
            ]
        )
    )

    logger.info(
        f"""
QUERY ANALYSIS

query={query}

complexity={
analysis["complexity"]
}

type={
analysis["query_type"]
}

estimated_sources={
analysis[
"estimated_sources"
]
}
"""
    )

    return {

        "analysis":
        analysis,

        "llm":
        llm
    }

# RESEARCH WRITER
writer_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a
world-class
research scientist,
technical analyst,
and intelligence writer.

Your goal:

Generate a DEEP,
evidence-grounded,
high-quality
research report.

DO NOT generate
shallow summaries.

You MUST:

1. synthesize evidence
2. resolve contradictions
3. explain uncertainty
4. mention conflicting views
5. ground findings
6. discuss long-term evolution
7. discuss future outlook

STRICT STRUCTURE:

# Executive Summary

# 40+ Year Historical Context

# Research Landscape

# Academic Findings

# Industry Findings

# Technical Foundations

# Contradictions & Debates

# Risks & Limitations

# Future Outlook

# Research Gaps

# Conclusion

# References

RULES:

- Minimum 2500 words
- Use evidence
- Avoid hallucination
- Mention uncertainty
- Never invent citations
- Prefer synthesis
over summarization
- Mention contradictions
- Stay technical
but readable
"""
        ),

        (
            "human",

            """
TOPIC:
{topic}

RESEARCH EVIDENCE:
{research}

Generate
a world-class
research report.
"""
        )
    ])
)

write_chain = (

    writer_prompt

    | reasoning_llm

    | StrOutputParser()
)

# CLAIM VERIFICATION

claim_verification_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a
claim verification agent.

Your task:

Verify whether claims
are supported by evidence.

For every claim:

Return:

{{
 "claim": "",
 "grounded": true/false,
 "confidence": "",
 "reason": ""
}}

STRICT RULES:

- no guessing
- no assumptions
- evidence only
- JSON only
"""
        ),

        (
            "human",

            """
CLAIMS:
{claims}

EVIDENCE:
{evidence}
"""
        )
    ])
)

claim_verification_chain = (

    claim_verification_prompt

    | critic_llm

    | StrOutputParser()
)

# CITATION VALIDATION
citation_validation_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You validate citations.

Your task:

Check:

1. citation exists
2. claim supported
3. citation quality
4. source reliability
5. weak evidence

Return JSON:

{{
 "citation_density": "",
 "missing_citations": [],
 "weak_citations": [],
 "validity_score": ""
}}

STRICT:

JSON ONLY
"""
        ),

        (
            "human",

            """
REPORT:

{report}

SOURCES:

{sources}
"""
        )
    ])
)

citation_validation_chain = (

    citation_validation_prompt

    | critic_llm

    | StrOutputParser()
)

# HALLUCINATION DETECTOR

hallucination_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a
hallucination detector.

Your job:

Find claims that:

- lack evidence
- overstate certainty
- contradict evidence
- seem fabricated
- contain unsupported facts

Return JSON:

{{
 "hallucination_risk": "",
 "risky_claims": [],
 "confidence": ""
}}

STRICT:

JSON ONLY
"""
        ),

        (
            "human",

            """
REPORT:
{report}

EVIDENCE:
{evidence}
"""
        )
    ])
)

hallucination_chain = (

    hallucination_prompt

    | critic_llm

    | StrOutputParser()
)

# CRITIC V3

critic_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a
senior research evaluator.

Evaluate the report.

Score:

1. Research depth
2. Citation density
3. Hallucination risk
4. Source diversity
5. Academic coverage
6. Freshness
7. Reliability
8. Contradiction handling
9. Technical depth

Output format:

# Overall Evaluation

## Final Score

## Strengths

## Weaknesses

## Missing Areas

## Hallucination Risks

## Improvement Suggestions

Be brutally honest.

Avoid fake praise.

Prioritize quality.
"""
        ),

        (
            "human",

            """
REPORT:

{report}
"""
        )
    ])
)

critic_chain = (

    critic_prompt

    | critic_llm

    | StrOutputParser()
)

# SAFE JSON PARSER
# Prevents JSON crashes

def safe_json_parse(
    raw_text
):

    try:

        return json.loads(
            raw_text
        )

    except Exception as e:

        logger.warning(
            f"JSON Parse Failed: "
            f"{str(e)}"
        )

        return {

            "status":
            "failed",

            "raw":
            raw_text
        }

# OBSERVABILITY

def log_agent_metrics(

    agent_name,

    execution_time,

    status="success",

    tokens=None
):

    logger.info(
        f"""
==================================

AGENT METRICS

agent={agent_name}

time={execution_time}s

status={status}

tokens={tokens}

==================================
"""
    )

# TEST

if __name__ == "__main__":

    query = (
        "Future of "
        "Quantum Security"
    )

    print("\n")
    print("=" * 70)
    print("PLANNER")
    print("=" * 70)

    plan = safe_planner(
        query
    )

    print(
        json.dumps(
            plan,
            indent=2
        )
    )

    print("\n")
    print("=" * 70)
    print("WRITER")
    print("=" * 70)

    report = (
        write_chain
        .invoke({

            "topic":
            query,

            "research":
            """
Quantum cryptography,
post-quantum encryption,
NIST standards,
Shor's algorithm,
industry adoption.
"""
        })
    )

    print(
        str(report)[:1500]
    )

    print("\n")
    print("=" * 70)
    print("CRITIC")
    print("=" * 70)

    feedback = (
        critic_chain
        .invoke({

            "report":
            str(report)
        })
    )

    print(
        feedback[:1000]
    )

    print("\n")
    print("=" * 70)
    print("HALLUCINATION")
    print("=" * 70)

    hallucination = (
        hallucination_chain
        .invoke({

            "report":
            str(report),

            "evidence":
            """
Quantum cryptography,
NIST PQC,
IEEE research
"""
        })
    )

    print(
        safe_json_parse(
            hallucination
        )
    )