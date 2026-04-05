import json
import logging
from google.genai.types import Part
from google.adk.tools import ToolContext

from .tools.client import client

IMAGE_PRODUCING_TOOLS = [
    "generate_image",
    "generate_image_with_reference",
    "edit_image",
    "remove_background",
    "composite_images",
    "overlay_text",
]

CRITIC_PROMPT = """You are a strict quality checker for AI-generated product images. Be critical — it is better to flag a potential issue than to miss one.

Context for this image: {context}

Fail the image (quality_ok: false) if ANY of the following are true:

1. **Text contrast** — any text is light-colored (white, cream, yellow, light gray) on a light background, OR dark text on a dark background. If there is any doubt about readability, fail it.
2. **Cropping** — any part of the subject, product, or text is cut off at the canvas edge, even slightly.
3. **Scale too small** — the main subject occupies less than ~30% of the image height. If it looks small or lost in the background, fail it.
4. **Scale too large** — the main subject is so large it is cropped or leaves no breathing room.
5. **Compositing artifacts** — any hard edges, halos, color fringing, or unnatural seams visible where elements were combined.
6. **Brief mismatch** — the result clearly does not match the context above.

Respond ONLY with a JSON object, no other text:
{{"quality_ok": true, "issues": []}}
or
{{"quality_ok": false, "issues": ["specific issue 1", "specific issue 2"]}}

When in doubt, fail it. A false positive is fine; a missed problem wastes the user's time."""


async def evaluate_image(image_part: Part, context: str) -> dict:
    """Evaluate a single image. Returns {"quality_ok": bool, "issues": list[str]}."""
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image_part, CRITIC_PROMPT.format(context=context)],
        )
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return {
            "quality_ok": bool(result.get("quality_ok", True)),
            "issues": result.get("issues", []),
        }
    except Exception as e:
        logging.warning(f"evaluate_image failed: {e}")
        return {"quality_ok": True, "issues": []}


def _get_context(tool_name: str, args: dict) -> str:
    return {
        "generate_image": args.get("prompt", ""),
        "generate_image_with_reference": args.get("prompt", ""),
        "edit_image": args.get("edit_prompt", ""),
        "remove_background": "background removal — subject should be cleanly isolated with transparent background",
        "composite_images": "compositing — foreground should be fully visible, well-scaled, and naturally placed on the background",
        "overlay_text": f"text overlay — the text \"{args.get('text', '')}\" should be clearly readable against the background",
    }.get(tool_name, "")


async def after_tool_critic(
    tool, args: dict, tool_context: ToolContext, tool_response: dict
) -> dict | None:
    """Evaluate every image-producing tool output and inject quality feedback."""
    tool_name = getattr(tool, "name", None) or getattr(tool, "__name__", str(tool))

    if tool_name not in IMAGE_PRODUCING_TOOLS:
        return None

    artifact_id = tool_response.get("tool_response_artifact_id")
    if not artifact_id or tool_response.get("status") != "success":
        return None

    try:
        image_part = await tool_context.load_artifact(filename=artifact_id)
        if image_part is None:
            return None

        context = _get_context(tool_name, args)
        evaluation = await evaluate_image(image_part, context)

        logging.info(f"Critic [{tool_name}]: quality_ok={evaluation['quality_ok']}, issues={evaluation['issues']}")

        return {
            **tool_response,
            "quality_ok": evaluation["quality_ok"],
            "quality_issues": evaluation["issues"],
        }

    except Exception as e:
        logging.warning(f"Critic evaluation failed for {tool_name}: {e}")
        return None
