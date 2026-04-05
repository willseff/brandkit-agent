import asyncio
import logging
from google import genai
from google.genai.types import Part
from google.adk.tools import ToolContext

from .client import client

N_CANDIDATES = 3   # images generated per round
MAX_ROUNDS = 2     # retry rounds if no candidate passes quality check
IMAGE_MODEL = "gemini-2.5-flash-image"


async def _generate_single(contents: list, config) -> Part | None:
    """Make one image generation call. Returns the image Part or None on failure."""
    try:
        response = await client.aio.models.generate_content(
            model=IMAGE_MODEL, contents=contents, config=config
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part
    except Exception as e:
        logging.warning(f"Single generation attempt failed: {e}")
    return None


async def generate_best_candidate(
    tool_context: ToolContext,
    contents: list,
    config,
    artifact_prefix: str,
    context: str,
) -> str:
    """
    Generate N_CANDIDATES images in parallel, evaluate each with the critic,
    and return the artifact ID of the best one (fewest issues).

    If no candidate passes quality in the first round, tries up to MAX_ROUNDS.
    Always returns the best candidate found, even if imperfect.
    """
    best_part: Part | None = None
    best_issue_count = float("inf")

    for round_num in range(MAX_ROUNDS):
        logging.info(
            f"generate_best_candidate: round {round_num + 1}/{MAX_ROUNDS}, "
            f"generating {N_CANDIDATES} candidates"
        )

        parts = await asyncio.gather(*[
            _generate_single(contents, config) for _ in range(N_CANDIDATES)
        ])
        parts = [p for p in parts if p is not None]

        if not parts:
            logging.warning(f"Round {round_num + 1}: all generations failed")
            continue

        from ..critic import evaluate_image  # lazy import — breaks circular dependency
        evaluations = await asyncio.gather(*[
            evaluate_image(p, context) for p in parts
        ])

        # Sort by issue count — fewer issues = better
        scored = sorted(zip(parts, evaluations), key=lambda x: len(x[1]["issues"]))
        round_best_part, round_best_eval = scored[0]
        round_issue_count = len(round_best_eval["issues"])

        logging.info(
            f"Round {round_num + 1} best: quality_ok={round_best_eval['quality_ok']}, "
            f"issues={round_best_eval['issues']}"
        )

        # Keep track of the overall best across rounds
        if round_issue_count < best_issue_count:
            best_part = round_best_part
            best_issue_count = round_issue_count

        if round_best_eval["quality_ok"]:
            break  # Good enough — stop generating

    if best_part is None:
        return ""

    artifact_id = f"{artifact_prefix}_{tool_context.function_call_id}.png"
    await tool_context.save_artifact(filename=artifact_id, artifact=best_part)
    return artifact_id
