from google import genai
from google.adk.tools import ToolContext
import logging

from .client import client


async def edit_image(
    tool_context: ToolContext,
    edit_prompt: str,
    image_artifact_ids: list[str] = [],
) -> dict[str, str]:
    """Edit an existing image or combine multiple images based on a text prompt.

    Use this to modify photos — change backgrounds, adjust lighting, add props,
    reposition elements, or combine multiple product images into one.

    Args:
        edit_prompt: Detailed description of the edit. BE VERY SPECIFIC.
                     Examples:
                     - "Change background to soft pure white with subtle gradient"
                     - "Add warm natural light from the left at 45 degrees"
                     - "Arrange these products in a horizontal line, evenly spaced"
        image_artifact_ids: List of image artifact IDs to edit or combine.
                           For single edits: ["product.png"]
                           For combining: ["product1.png", "product2.png"]

    Returns:
        dict with keys:
            - 'tool_response_artifact_id': Artifact ID for the edited image
            - 'tool_input_artifact_ids': Input artifact IDs used
            - 'edit_prompt': The full edit prompt used
            - 'status': Success or error status
            - 'message': Additional information
    """
    try:
        if not image_artifact_ids:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "tool_input_artifact_ids": "",
                "edit_prompt": edit_prompt,
                "message": "No images provided. Please provide image_artifact_ids.",
            }

        # Load all images
        image_artifacts = []
        for img_id in image_artifact_ids:
            artifact = await tool_context.load_artifact(filename=img_id)
            if artifact is None:
                return {
                    "status": "error",
                    "tool_response_artifact_id": "",
                    "tool_input_artifact_ids": "",
                    "edit_prompt": edit_prompt,
                    "message": f"Artifact {img_id} not found",
                }
            image_artifacts.append(artifact)

        # Build full prompt with preservation instructions
        if len(image_artifacts) > 1:
            full_prompt = (
                f"{edit_prompt}. "
                f"Combine these {len(image_artifacts)} images together. "
                "IMPORTANT: Preserve each product's original appearance faithfully."
            )
        else:
            full_prompt = (
                f"{edit_prompt}. "
                "IMPORTANT: Preserve the product's original appearance faithfully."
            )

        contents = image_artifacts + [full_prompt]

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents,
            config=genai.types.GenerateContentConfig(
                response_modalities=["Image"],
            ),
        )

        artifact_id = ""
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                artifact_id = f"edit_img_{tool_context.function_call_id}.png"
                await tool_context.save_artifact(filename=artifact_id, artifact=part)

        return {
            "status": "success",
            "tool_response_artifact_id": artifact_id,
            "tool_input_artifact_ids": ", ".join(image_artifact_ids),
            "edit_prompt": full_prompt,
            "message": f"Image edited successfully using {len(image_artifacts)} input(s)",
        }
    except Exception as e:
        logging.error(e)
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "tool_input_artifact_ids": ", ".join(image_artifact_ids)
            if image_artifact_ids
            else "",
            "edit_prompt": edit_prompt,
            "message": f"Error editing image: {str(e)}",
        }
