from google.adk.tools import ToolContext
from google.genai.types import Part
from io import BytesIO
import logging

try:
    from rembg import remove as rembg_remove
    from PIL import Image
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False


async def remove_background(
    tool_context: ToolContext,
    image_artifact_id: str,
) -> dict[str, str]:
    """Remove the background from an image, making it transparent.

    Use this to isolate a product from its background. The result will have
    a transparent background (PNG with alpha channel), ready for compositing.

    Args:
        image_artifact_id: Artifact ID of the image to process.

    Returns:
        dict with keys:
            - 'tool_response_artifact_id': Artifact ID for the result
            - 'input_artifact_id': The input artifact ID
            - 'status': Success or error status
            - 'message': Additional information
    """
    if not REMBG_AVAILABLE:
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "input_artifact_id": image_artifact_id,
            "message": "rembg library not available. Install with: pip install rembg",
        }

    try:
        artifact = await tool_context.load_artifact(filename=image_artifact_id)
        if artifact is None:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "input_artifact_id": image_artifact_id,
                "message": f"Artifact {image_artifact_id} not found",
            }

        # Get image bytes from artifact
        input_bytes = artifact.inline_data.data

        # Open with PIL, remove background
        input_image = Image.open(BytesIO(input_bytes))
        output_image = rembg_remove(input_image)

        # Save result to bytes
        output_buffer = BytesIO()
        output_image.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()

        # Save as artifact
        result_id = f"nobg_{tool_context.function_call_id}.png"
        result_part = Part(
            inline_data={"mime_type": "image/png", "data": output_bytes}
        )
        await tool_context.save_artifact(filename=result_id, artifact=result_part)

        return {
            "status": "success",
            "tool_response_artifact_id": result_id,
            "input_artifact_id": image_artifact_id,
            "message": "Background removed successfully",
        }
    except Exception as e:
        logging.error(e)
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "input_artifact_id": image_artifact_id,
            "message": f"Error removing background: {str(e)}",
        }
