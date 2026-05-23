
import time
import logging
from typing import (
    Dict,
    List,
    Any
)

from backend.agents import (
    query_planner_chain,
    write_chain,
    critic_chain
)

from backend.tools import (

    web_Search,

    scrape_url,

    run_multi_retrieval
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
    "ResearchPipelineV3"
)

# TIMESTAMP

def timestamp():

    return time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

# QUERY COMPLEXITY

def estimate_complexity(
    planner_result: dict
):

    complexity = (
        planner_result.get(
            "complexity",
            "medium"
        )
    )

    intent = (
        planner_result.get(
            "intent",
            ""
        )
    )

    if (
        complexity == "low"
    ):

        return "quick"

    elif (

        complexity == "medium"

        or

        intent in [

            "technical",

            "market_research"
        ]
    ):

        return "research"

    return "deep"

# CONTRADICTION GROUPING

def group_evidence_by_signal(
    ranked_sources
):

    supporting = []

    contradictory = []

    neutral = []

    contradiction_words = [

        "however",

        "contrary",

        "challenge",

        "limitation",

        "not effective",

        "fails",

        "risk",

        "debate",

        "uncertain"
    ]

    for item in ranked_sources:

        content = str(

            item.get(
                "content",
                ""
            )

        ).lower()

        contradiction_flag = any(

            word in content

            for word in
            contradiction_words
        )

        if contradiction_flag:

            contradictory.append(
                item
            )

        elif (

            item.get(
                "trust_score",
                0
            ) >= 8
        ):

            supporting.append(
                item
            )

        else:

            neutral.append(
                item
            )

    return {

        "supporting":
        supporting,

        "contradictory":
        contradictory,

        "neutral":
        neutral
    }

# SOURCE EXPLORER

def build_source_explorer(
    ranked_sources
):

    explorer = []

    for idx, item in enumerate(

        ranked_sources,

        start=1
    ):

        explorer.append({

            "rank":
            idx,

            "title":
            item.get(
                "title",
                "Unknown"
            ),

            "source":
            item.get(
                "source",
                "unknown"
            ),

            "url":
            item.get(
                "url",
                ""
            ),

            "trust_score":
            item.get(
                "trust_score",
                0
            ),

            "final_score":
            item.get(
                "final_score",
                0
            ),

            "published":
            item.get(
                "published",
                "Unknown"
            )
        })

    return explorer

# PIPELINE

def run_research_pipeline(

    topic: str,

    mode: str = None,

    filters: dict = None
):

    if not topic.strip():

        raise ValueError(
            "Topic cannot be empty."
        )

    # INITIAL STATE

    state = {

        "topic":
        topic,

        "query_plan":
        {},

        "sources":
        [],

        "ranked_sources":
        [],

        "source_explorer":
        [],

        "evidence_groups":
        {},

        "scraped_sources":
        [],

        "report":
        "",

        "feedback":
        "",

        "logs":
        [],

        "metadata":
        {}
    }

    try:

        pipeline_start = (
            time.time()
        )

        logger.info(
            "=" * 70
        )

        logger.info(
            f"PIPELINE STARTED "
            f"| Topic={topic}"
        )

        logger.info(
            "=" * 70
        )

        # STEP 1
        # QUERY PLANNER

        print("\n")
        print("=" * 70)
        print(
            "STEP 1: "
            "QUERY PLANNER"
        )
        print("=" * 70)

        planner_start = (
            time.time()
        )

        planner_result = (

            query_planner_chain

            .invoke({

                "query":
                topic
            })
        )

        planner_time = round(

            time.time()

            - planner_start,

            2
        )

        state[
            "query_plan"
        ] = planner_result

        logger.info(
            "Generated Query Plan"
        )

        print("\n")
        print(
            planner_result
        )

        # MODE ESTIMATION

        auto_mode = (
            estimate_complexity(
                planner_result
            )
        )

        selected_mode = (
            mode
            if mode
            else auto_mode
        )

        logger.info(
            f"Research Mode: "
            f"{selected_mode.upper()}"
        )

        subqueries = (
            planner_result.get(
                "subqueries",
                []
            )
        )

        if not subqueries:

            subqueries = [
                topic
            ]

        state["logs"].append({

            "stage":
            "planner",

            "agent":
            "Query Planner",

            "status":
            "success",

            "execution_time":
            planner_time,

            "subqueries":
            subqueries,

            "complexity":
            planner_result.get(
                "complexity"
            ),

            "intent":
            planner_result.get(
                "intent"
            )
        })

        # STEP 2
        # DEEP RETRIEVAL

        print("\n")
        print("=" * 70)
        print(
            "STEP 2: "
            "DEEP RETRIEVAL"
        )
        print("=" * 70)

        retrieval_start = (
            time.time()
        )

        all_results = []

        for idx, subquery in enumerate(

            subqueries[:5],

            start=1
        ):

            logger.info(
                f"[{idx}] "
                f"Searching: "
                f"{subquery}"
            )

            print(
                f"\nSearching: "
                f"{subquery}"
            )

            try:

                retrieval_results = (

                    run_multi_retrieval(

                        query=subquery,

                        mode=
                        selected_mode,

                        filters=
                        filters
                    )
                )

                all_results.extend(
                    retrieval_results
                )

            except Exception as e:

                logger.error(
                    f"Retrieval Failed: "
                    f"{str(e)}"
                )

                continue

        retrieval_time = round(

            time.time()

            - retrieval_start,

            2
        )

        state[
            "sources"
        ] = all_results

        print(
            f"\nRetrieved "
            f"{len(all_results)} "
            f"sources"
        )

        logger.info(
            f"Retrieved "
            f"{len(all_results)} "
            f"sources"
        )

        # SOURCE EXPLORER

        source_explorer = (
            build_source_explorer(
                all_results
            )
        )

        state[
            "source_explorer"
        ] = source_explorer

        # EVIDENCE GROUPING

        evidence_groups = (
            group_evidence_by_signal(
                all_results
            )
        )

        state[
            "evidence_groups"
        ] = evidence_groups

        state["logs"].append({

            "stage":
            "retrieval",

            "agent":
            "Deep Retrieval",

            "status":
            "success",

            "execution_time":
            retrieval_time,

            "sources_found":
            len(
                all_results
            ),

            "mode":
            selected_mode
        })

        # STEP 3
        # EVIDENCE EXTRACTION

        print("\n")
        print("=" * 70)
        print(
            "STEP 3: "
            "EVIDENCE EXTRACTION"
        )
        print("=" * 70)

        scrape_start = (
            time.time()
        )

        scraped_content = []

        # TOP SOURCES ONLY
        # Prevent latency explosion

        max_scrapes = {

            "quick": 5,

            "research": 12,

            "deep": 20

        }.get(
            selected_mode,
            12
        )

        top_sources = (
            all_results[
                :max_scrapes
            ]
        )

        for idx, source in enumerate(

            top_sources,

            start=1
        ):

            try:

                url = source.get(
                    "url"
                )

                if not url:
                    continue

                print(
                    f"Scraping "
                    f"{idx}/"
                    f"{len(top_sources)}"
                )

                logger.info(
                    f"Scraping: "
                    f"{url}"
                )

                scraped = (
                    scrape_url.invoke({
                        "url":
                        url
                    })
                )

                if (

                    scraped

                    and

                    isinstance(
                        scraped,
                        dict
                    )

                    and

                    scraped.get(
                        "status"
                    ) == "success"
                ):

                    scraped_content.append({

                        "title":
                        source.get(
                            "title",
                            "Unknown"
                        ),

                        "url":
                        url,

                        "content":
                        scraped.get(
                            "content",
                            ""
                        ),

                        "trust_score":
                        source.get(
                            "trust_score",
                            5
                        ),

                        "final_score":
                        source.get(
                            "final_score",
                            5
                        ),

                        "source":
                        source.get(
                            "source",
                            "unknown"
                        )
                    })

            except Exception as e:

                logger.warning(
                    f"Scraping Failed: "
                    f"{str(e)}"
                )

                continue

        scrape_time = round(

            time.time()

            - scrape_start,

            2
        )

        state[
            "scraped_sources"
        ] = scraped_content

        state["logs"].append({

            "stage":
            "scraping",

            "agent":
            "Evidence Extraction",

            "status":
            "success",

            "execution_time":
            scrape_time,

            "scraped_count":
            len(
                scraped_content
            )
        })

        logger.info(
            f"Scraped "
            f"{len(scraped_content)} "
            f"sources"
        )

        # STEP 4
        # GROUNDED WRITER

        print("\n")
        print("=" * 70)
        print(
            "STEP 4: "
            "RESEARCH WRITER"
        )
        print("=" * 70)

        writer_start = (
            time.time()
        )

        evidence_text = ""

        # SUPPORTING EVIDENCE

        evidence_text += (
            "\n\n"
            "=== SUPPORTING "
            "EVIDENCE ===\n\n"
        )

        for item in (
            evidence_groups[
                "supporting"
            ][:12]
        ):

            evidence_text += f"""

TITLE:
{item.get("title")}

SOURCE:
{item.get("source")}

URL:
{item.get("url")}

TRUST SCORE:
{item.get("trust_score")}

CONTENT:
{str(item.get("content"))[:2500]}

"""

        # CONTRADICTORY EVIDENCE

        if evidence_groups[
            "contradictory"
        ]:

            evidence_text += (
                "\n\n"
                "=== "
                "CONTRADICTORY "
                "EVIDENCE ===\n\n"
            )

            for item in (
                evidence_groups[
                    "contradictory"
                ][:8]
            ):

                evidence_text += f"""

TITLE:
{item.get("title")}

SOURCE:
{item.get("source")}

URL:
{item.get("url")}

CONTENT:
{str(item.get("content"))[:1800]}

"""

        # PDF EVIDENCE

        pdf_sources = [

            s for s in
            all_results

            if s.get(
                "source"
            ) == "pdf"
        ]

        if pdf_sources:

            evidence_text += (
                "\n\n"
                "=== PDF "
                "KNOWLEDGE "
                "BASE ===\n\n"
            )

            for pdf in (
                pdf_sources[:10]
            ):

                evidence_text += f"""

PDF SOURCE:
{pdf.get("title")}

CONTENT:
{str(pdf.get("content"))[:2000]}

"""

        # WRITE REPORT

        report = (
            write_chain.invoke({

                "topic":
                topic,

                "research":
                evidence_text
            })
        )

        writer_time = round(

            time.time()

            - writer_start,

            2
        )

        state[
            "report"
        ] = report

        state["logs"].append({

            "stage":
            "writer",

            "agent":
            "Research Writer",

            "status":
            "success",

            "execution_time":
            writer_time
        })

        logger.info(
            "Writer Complete"
        )

        # STEP 5
        # CRITIC V2

        print("\n")
        print("=" * 70)
        print(
            "STEP 5: "
            "CRITIC"
        )
        print("=" * 70)

        critic_start = (
            time.time()
        )

        feedback = (
            critic_chain.invoke({

                "report":
                report
            })
        )

        critic_time = round(

            time.time()

            - critic_start,

            2
        )

        state[
            "feedback"
        ] = feedback

        state["logs"].append({

            "stage":
            "critic",

            "agent":
            "Critic",

            "status":
            "success",

            "execution_time":
            critic_time
        })

        # METADATA

        total_time = round(

            time.time()

            - pipeline_start,

            2
        )

        state[
            "metadata"
        ] = {

            "pipeline_status":
            "success",

            "execution_time":
            total_time,

            "mode":
            selected_mode,

            "sources":
            len(
                all_results
            ),

            "scraped":
            len(
                scraped_content
            ),

            "supporting_sources":
            len(
                evidence_groups[
                    "supporting"
                ]
            ),

            "contradictory_sources":
            len(
                evidence_groups[
                    "contradictory"
                ]
            ),

            "query_type":
            planner_result.get(
                "intent",
                "unknown"
            )
        }

        logger.info(
            "=" * 70
        )

        logger.info(
            f"PIPELINE COMPLETE "
            f"| {total_time}s"
        )

        logger.info(
            "=" * 70
        )

        return state

    except Exception as e:

        logger.error(
            f"Pipeline Failed: "
            f"{str(e)}"
        )

        return {

            "status":
            "failed",

            "error":
            str(e),

            "report":
            "",

            "feedback":
            "",

            "source_explorer":
            [],

            "metadata":
            {},

            "logs":
            state.get(
                "logs",
                []
            )
        }

# LOCAL TEST

if __name__ == "__main__":

    topic = input(
        "\nTopic: "
    )

    result = (
        run_research_pipeline(

            topic=topic,

            mode="deep",

            filters={

                "year_from":
                2018,

                "min_citations":
                20
            }
        )
    )

    print("\n")
    print("=" * 70)
    print("FINAL REPORT")
    print("=" * 70)

    print(
        result[
            "report"
        ][:3000]
    )

    print("\n")
    print("=" * 70)
    print("METADATA")
    print("=" * 70)

    print(
        result[
            "metadata"
        ]
    )