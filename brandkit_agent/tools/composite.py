from google.adk.tools import ToolContext
from google.genai.types import Part
from PIL import Image
from io import BytesIO
import logging


async def composite_images(
    tool_context: ToolContext,
    foreground_artifact_id: str,
    background_artifact_id: str,
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
) -> dict[str, str]:
    """Overlay a foreground image onto a background image.

    Use this to place a product (with transparent background) onto a scene
    or background image. Works best when the foreground has had its background
    removed first.

    Args:
        foreground_artifact_id: Artifact ID of the foreground image (e.g., product with transparent bg).
        background_artifact_id: Artifact ID of the background image.
        x: X position (pixels from left) to place the foreground. Defaults to 0.
        y: Y position (pixels from top) to place the foreground. Defaults to 0.
        scale: Scale factor for the foreground. 1.0 = original size, 0.5 = half, 2.0 = double.

    Returns:
        dict with keys:
            - 'tool_response_artifact_id': Artifact ID for the composited image
            - 'foreground_artifact_id': The foreground input ID
            - 'background_artifact_id': The background input ID
            - 'status': Success or error status
            - 'message': Additional information
    """
    try:
        fg_artifact = await tool_context.load_artifact(filename=foreground_artifact_id)
        bg_artifact = await tool_context.load_artifact(filename=background_artifact_id)

        if fg_artifact is None:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "foreground_artifact_id": foreground_artifact_id,
                "background_artifact_id": background_artifact_id,
                "message": f"Foreground artifact {foreground_artifact_id} not found",
            }
        if bg_artifact is None:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "foreground_artifact_id": foreground_artifact_id,
                "background_artifact_id": background_artifact_id,
                "message": f"Background artifact {background_artifact_id} not found",
            }

        # Load images
        fg_image = Image.open(BytesIO(fg_artifact.inline_data.data)).convert("RGBA")
        bg_image = Image.open(BytesIO(bg_artifact.inline_data.data)).convert("RGBA")

        # Scale foreground
        if scale != 1.0:
            new_w = int(fg_image.width * scale)
            new_h = int(fg_image.height * scale)
            fg_image = fg_image.resize((new_w, new_h), Image.LANCZOS)

        # Composite
        result = bg_image.copy()
        result.paste(fg_image, (x, y), fg_image)

        # Save
        output_buffer = BytesIO()
        result.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()

        result_id = f"comp_{tool_context.function_call_id}.png"
        result_part = Part(
            inline_data={"mime_type": "image/png", "data": output_bytes}
        )
        await tool_context.save_artifact(filename=result_id, artifact=result_part)

        return {
            "status": "success",
            "tool_response_artifact_id": result_id,
            "foreground_artifact_id": foreground_artifact_id,
            "background_artifact_id": background_artifact_id,
            "message": f"Images composited at ({x}, {y}) with scale {scale}",
        }
    except Exception as e:
        logging.error(e)
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "foreground_artifact_id": foreground_artifact_id,
            "background_artifact_id": background_artifact_id,
            "message": f"Error compositing images: {str(e)}",
        }
