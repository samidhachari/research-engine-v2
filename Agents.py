import os
import warnings

from dotenv import load_dotenv

from langchain_mistralai import (
    ChatMistralAI
)

from langchain_core.prompts import (
    ChatPromptTemplate
)

from langchain_core.output_parsers import (
    StrOutputParser,
    JsonOutputParser
)

warnings.filterwarnings(
    "ignore"
)

load_dotenv()

# ==========================================
# API KEY
# ==========================================

MISTRAL_API_KEY = os.getenv(
    "MISTRAL_API_KEY"
)

if not MISTRAL_API_KEY:

    raise ValueError(
        "MISTRAL_API_KEY "
        "missing in .env"
    )

# ==========================================
# LLM
# ==========================================

llm = ChatMistralAI(

    model=
    "mistral-small-latest",

    api_key=
    MISTRAL_API_KEY,

    temperature=0.2,

    max_tokens=8000,

    timeout=180,

    max_retries=3
)

# ==========================================
# QUERY PLANNER V2
# ==========================================

planner_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a world-class
research planning engine.

Your goal is to deeply
understand a research problem
before retrieval starts.

You MUST:

1. Understand intent
2. Classify complexity
3. Decompose research
4. Generate high-value
subqueries
5. Extract entities
6. Choose retrieval strategy
7. Estimate time horizon
8. Recommend source types

Return ONLY VALID JSON.

Do NOT explain anything.

JSON FORMAT:

{
    "main_query": "",

    "intent": "",

    "complexity": "",

    "time_horizon": "",

    "search_depth": "",

    "subqueries": [],

    "entities": [],

    "source_types": [],

    "retrieval_strategy": "",

    "reasoning_type": "",

    "priority_order": []
}

INTENTS:
- academic
- technical
- market_research
- factual
- news
- deep_research

COMPLEXITY:
- low
- medium
- high

SEARCH DEPTH:
- low
- medium
- high

RETRIEVAL STRATEGY:
- simple
- multi-hop
- comparative
- temporal

REASONING:
- analytical
- comparative
- causal
- predictive

SUBQUERY RULES:

Simple Query:
1–2 subqueries

Complex Query:
2–3 strong subqueries

Deep Research:
4–5 evidence-rich
subqueries.

Avoid overlap.

Generate only
high-signal searches.
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

    | llm

    | JsonOutputParser()
)

# WRITER V2

writer_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a world-class
research intelligence engine.

Your responsibility:

Produce deeply researched,
evidence-grounded,
citation-backed reports.

CRITICAL RULES:

1. NEVER hallucinate.

2. ONLY use
retrieved evidence.

3. Every major claim
must reference evidence.

4. Mention uncertainty
when evidence is weak.

5. Resolve contradictions
across sources.

6. Prefer synthesis,
not summarization.

7. Provide historical,
technical, academic,
industry and future context.

8. Reports must feel:

- expert-level
- trustworthy
- deeply researched
- structured
- long-form

Target:
2500–4000 words.

Write with professional
clarity.

Avoid fluff.
"""
        ),

        (
            "human",

            """
Create a deep research report.

TOPIC:
{topic}

RESEARCH EVIDENCE:
{research}

REQUIRED STRUCTURE:

# Executive Summary

# Historical Context
(40+ years if relevant)

# Research Landscape

# Academic Findings

# Industry Findings

# Technical Foundations

# Major Contradictions

# Risks & Challenges

# Future Outlook

# Expert Opinions

# Research Gaps

# Conclusion

# References

IMPORTANT:

Every section should
be evidence grounded.

Mention URLs when relevant.

Never invent sources.
"""
        )
    ])
)

write_chain = (

    writer_prompt

    | llm

    | StrOutputParser()
)

# CRITIC V2

critic_prompt = (
    ChatPromptTemplate
    .from_messages([

        (
            "system",

            """
You are a strict
research quality evaluator.

Evaluate based on:

1. Research Depth
2. Citation Grounding
3. Source Diversity
4. Academic Coverage
5. Factual Reliability
6. Hallucination Risk
7. Structural Quality
8. Reasoning Quality
9. Freshness
10. Trustworthiness

Be brutally honest.

Weak research
must be criticized.
"""
        ),

        (
            "human",

            """
Evaluate this report.

REPORT:

{report}

Return EXACTLY:

Research Depth: X/10
Citation Density: X/10
Source Diversity: X/10
Academic Coverage: X/10
Freshness: X/10
Reliability: X/10
Hallucination Risk:
Low/Medium/High
Overall Score: X/10

Strengths:
- ...

Weaknesses:
- ...

Missing Areas:
- ...

Final Verdict:
...
"""
        )
    ])
)

critic_chain = (

    critic_prompt

    | llm

    | StrOutputParser()
)

# TEST

if __name__ == "__main__":

    result = (
        query_planner_chain
        .invoke({

            "query":
            "Future of Quantum Security"
        })
    )

    print("\n")
    print(result)



# Changes:

# removed build_search_agent()
# removed build_scrape_agent()
# planner v2
# deep writer
# hallucination reduction
# 40+ year context
# evidence grounding
# stronger critic
# long-form research generation