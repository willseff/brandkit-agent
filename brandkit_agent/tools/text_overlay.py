from google.adk.tools import ToolContext
from google.genai.types import Part
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import logging


async def overlay_text(
    tool_context: ToolContext,
    image_artifact_id: str,
    text: str,
    x: int,
    y: int,
    font_size: int = 40,
    color: str = "#FFFFFF",
) -> dict[str, str]:
    """Render text onto an image at a specified position.

    Use this to add branding, labels, prices, or any text to product images.

    Args:
        image_artifact_id: Artifact ID of the image to add text to.
        text: The text to render.
        x: X position (pixels from left) for the text.
        y: Y position (pixels from top) for the text.
        font_size: Size of the font in pixels. Defaults to 40.
        color: Text color as hex string (e.g., "#FFFFFF" for white, "#000000" for black).

    Returns:
        dict with keys:
            - 'tool_response_artifact_id': Artifact ID for the result
            - 'input_artifact_id': The input artifact ID
            - 'text': The text that was rendered
            - 'status': Success or error status
            - 'message': Additional information
    """
    try:
        artifact = await tool_context.load_artifact(filename=image_artifact_id)
        if artifact is None:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "input_artifact_id": image_artifact_id,
                "text": text,
                "message": f"Artifact {image_artifact_id} not found",
            }

        # Load image
        image = Image.open(BytesIO(artifact.inline_data.data)).convert("RGBA")
        draw = ImageDraw.Draw(image)

        # Load font — use default if custom fonts aren't available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default(size=font_size)

        # Draw text
        draw.text((x, y), text, fill=color, font=font)

        # Save
        output_buffer = BytesIO()
        image.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()

        result_id = f"text_{tool_context.function_call_id}.png"
        result_part = Part(
            inline_data={"mime_type": "image/png", "data": output_bytes}
        )
        await tool_context.save_artifact(filename=result_id, artifact=result_part)

        return {
            "status": "success",
            "tool_response_artifact_id": result_id,
            "input_artifact_id": image_artifact_id,
            "text": text,
            "message": f"Text '{text}' added at ({x}, {y}) with size {font_size}",
        }
    except Exception as e:
        logging.error(e)
        return {
            "status": "error",
            "tool_response_artifact_id": "",
            "input_artifact_id": image_artifact_id,
            "text": text,
            "message": f"Error adding text: {str(e)}",
        }
