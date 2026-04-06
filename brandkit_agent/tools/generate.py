from google import genai
from google.adk.tools import ToolContext
import logging

from .client import client
from ..config import IMAGE_MODEL


async def generate_image(
    tool_context: ToolContext,
    prompt: str,
    aspect_ratio: str = "1:1",
) -> dict[str, str]:
    """Generate a new image from a text prompt.

    Use this to create images from scratch — backgrounds, scenes, props, etc.

    Args:
        prompt: Detailed description of the image to generate. Be specific about
                style, colors, composition, lighting, and mood.
                Examples:
                - "A marble countertop in a bright modern kitchen with warm natural light"
                - "Minimalist white background with soft gradient, studio photography style"
        aspect_ratio: Aspect ratio of the generated image. Options: "1:1", "16:9", "9:16", "4:3", "3:4".
                      Defaults to "1:1".

    Returns:
        dict with keys:
            - 'tool_response_artifact_id': Artifact ID for the generated image
            - 'prompt': The prompt used
            - 'status': Success or error status
            - 'message': Additional information
    """
    try:
        response = await client.aio.models.generate_content(
            model=IMAGE_MODEL,
            contents=[prompt],
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
                artifact_id = f"gen_img_{tool_context.function_call_id}.png"
                await tool_context.save_artifact(filename=artifact_id, artifact=part)

        return {
            "status": "success",
            "tool_response_artifact_id": artifact_id,
            "prompt": prompt,
            "message": "Image generated successfully",
        }
    except Exception as e:
        logging.error(e)
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "prompt": prompt,
            "message": f"Error generating image: {str(e)}",
        }
