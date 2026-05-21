from AAgents import (
    write_chain,
    critic_chain,
    query_planner_chain
)

from tools import (
    web_Search,
    scrape_url
)

import logging
import time

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
    __name__
)

# PIPELINE

def run_research_pipeline(
    topic: str
):

    if not topic.strip():

        raise ValueError(
            "Topic cannot be empty."
        )

    state = {

        "topic":
        topic,

        "query_plan":
        {},

        "sources":
        [],

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
            f"Pipeline Started | "
            f"Topic={topic}"
        )

        # STEP 1 — QUERY PLANNER

        print("\n" + "=" * 60)
        print("STEP 1: QUERY PLANNER")
        print("=" * 60)

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

            "agent":
            "Query Planner",

            "status":
            "success",

            "execution_time":
            planner_time,

            "subqueries":
            subqueries
        })

        print(
            planner_result
        )

        # STEP 2 — DEEP RETRIEVAL

        print("\n" + "=" * 60)
        print("STEP 2: DEEP RETRIEVAL")
        print("=" * 60)

        retrieval_start = (
            time.time()
        )

        all_results = []

        for subquery in (
            subqueries[:3]
        ):

            print(
                f"\nSearching: "
                f"{subquery}"
            )

            search_results = (
                web_Search.invoke({

                    "query":
                    subquery,

                    "deep_mode":
                    True
                })
            )

            all_results.extend(
                search_results
            )

        retrieval_time = round(

            time.time()
            - retrieval_start,

            2
        )

        state[
            "sources"
        ] = all_results

        state["logs"].append({

            "agent":
            "Deep Retrieval",

            "status":
            "success",

            "execution_time":
            retrieval_time,

            "sources_found":
            len(
                all_results
            )
        })

        print(
            f"\nRetrieved "
            f"{len(all_results)} "
            f"sources"
        )

        # STEP 3 — EVIDENCE SCRAPING

        print("\n" + "=" * 60)
        print("STEP 3: EVIDENCE EXTRACTION")
        print("=" * 60)

        scrape_start = (
            time.time()
        )

        scraped_content = []

        top_sources = (
            all_results[:15]
        )

        for idx, source in enumerate(
            top_sources
        ):

            try:

                url = source.get(
                    "url"
                )

                if not url:
                    continue

                print(
                    f"Scraping "
                    f"{idx+1}/15"
                )

                content = (
                    scrape_url.invoke({
                        "url":
                        url
                    })
                )

                if content:

                    scraped_content.append({

                        "title":
                        source.get(
                            "title"
                        ),

                        "url":
                        url,

                        "content":
                        content,

                        "score":
                        source.get(
                            "final_score",
                            0
                        )
                    })

            except Exception:

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

        # STEP 4 — RESEARCH WRITER

        print("\n" + "=" * 60)
        print("STEP 4: WRITER")
        print("=" * 60)

        writer_start = (
            time.time()
        )

        evidence_text = ""

        for item in (
            scraped_content
        ):

            evidence_text += f"""

SOURCE:
{item["title"]}

URL:
{item["url"]}

CONTENT:
{item["content"][:3000]}

"""

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

            "agent":
            "Writer",

            "status":
            "success",

            "execution_time":
            writer_time
        })

        # STEP 5 — CRITIC

        print("\n" + "=" * 60)
        print("STEP 5: CRITIC")
        print("=" * 60)

        critic_start = (
            time.time()
        )

        feedback = (
            critic_chain
            .invoke({

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

            "sources":
            len(
                all_results
            ),

            "scraped":
            len(
                scraped_content
            )
        }

        logger.info(
            f"Pipeline Finished "
            f"| {total_time}s"
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
            topic
        )
    )

    print("\n")
    print(result["report"])
