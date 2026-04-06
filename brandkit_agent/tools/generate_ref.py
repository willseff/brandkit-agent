from google import genai
from google.adk.tools import ToolContext
import logging

from .client import client
from ..config import IMAGE_MODEL


async def generate_image_with_reference(
    tool_context: ToolContext,
    prompt: str,
    reference_artifact_ids: list[str] = [],
    aspect_ratio: str = "1:1",
) -> dict[str, str]:
    """Generate a new image guided by reference images.

    Use this when you need to create something that matches the style, subject,
    or look of existing images. Great for subject consistency, style transfer,
    and creating variations.

    Args:
        prompt: What to generate, referencing the provided images. Be specific.
                Examples:
                - "Same product but in blue color, same style and lighting"
                - "Generate a similar scene but with autumn colors"
                - "Create a product photo in the same style as the reference"
        reference_artifact_ids: List of artifact IDs to use as references.
                                Supports up to 14 reference images.
        aspect_ratio: Aspect ratio. Options: "1:1", "16:9", "9:16", "4:3", "3:4".

    Returns:
        dict with keys:
            - 'tool_response_artifact_id': Artifact ID for the generated image
            - 'reference_artifact_ids': The reference IDs used
            - 'prompt': The prompt used
            - 'status': Success or error status
            - 'message': Additional information
    """
    try:
        if not reference_artifact_ids:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "reference_artifact_ids": "",
                "prompt": prompt,
                "message": "No reference images provided.",
            }

        # Load reference images
        ref_artifacts = []
        for ref_id in reference_artifact_ids:
            artifact = await tool_context.load_artifact(filename=ref_id)
            if artifact is None:
                return {
                    "status": "error",
                    "tool_response_artifact_id": "",
                    "reference_artifact_ids": ", ".join(reference_artifact_ids),
                    "prompt": prompt,
                    "message": f"Reference artifact {ref_id} not found",
                }
            ref_artifacts.append(artifact)

        # Build contents: references first, then prompt
        contents = ref_artifacts + [prompt]

        response = await client.aio.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                response_modalities=["Image"],
                image_config=genai.types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                ),
            ),
        )

        artifact_id = ""
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                artifact_id = f"genref_img_{tool_context.function_call_id}.png"
                await tool_context.save_artifact(filename=artifact_id, artifact=part)

        return {
            "status": "success",
            "tool_response_artifact_id": artifact_id,
            "reference_artifact_ids": ", ".join(reference_artifact_ids),
            "prompt": prompt,
            "message": f"Image generated with {len(ref_artifacts)} reference(s)",
        }
    except Exception as e:
        logging.error(e)
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "reference_artifact_ids": ", ".join(reference_artifact_ids)
            if reference_artifact_ids
            else "",
            "prompt": prompt,
            "message": f"Error generating image: {str(e)}",
        }
