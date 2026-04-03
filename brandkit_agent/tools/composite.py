from google.adk.tools import ToolContext
from google.genai.types import Part
from PIL import Image
from io import BytesIO
import logging

# Valid position presets
POSITION_PRESETS = [
    "center",
    "center-top",
    "center-bottom",
    "left-center",
    "right-center",
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
]


def _calculate_position(
    position: str, fg_w: int, fg_h: int, bg_w: int, bg_h: int
) -> tuple[int, int]:
    """Calculate x, y from a position preset."""
    positions = {
        "center": ((bg_w - fg_w) // 2, (bg_h - fg_h) // 2),
        "center-top": ((bg_w - fg_w) // 2, 0),
        "center-bottom": ((bg_w - fg_w) // 2, bg_h - fg_h),
        "left-center": (0, (bg_h - fg_h) // 2),
        "right-center": (bg_w - fg_w, (bg_h - fg_h) // 2),
        "top-left": (0, 0),
        "top-right": (bg_w - fg_w, 0),
        "bottom-left": (0, bg_h - fg_h),
        "bottom-right": (bg_w - fg_w, bg_h - fg_h),
    }
    return positions.get(position, positions["center"])


async def composite_images(
    tool_context: ToolContext,
    foreground_artifact_id: str,
    background_artifact_id: str,
    position: str = "center",
    scale: float = 1.0,
    x_offset: int = 0,
    y_offset: int = 0,
) -> dict[str, str]:
    """Overlay a foreground image onto a background image.

    Use this to place a product (with transparent background) onto a scene
    or background image. Works best when the foreground has had its background
    removed first.

    IMPORTANT: Use position presets instead of raw coordinates.
    After placement, use x_offset and y_offset to nudge from the preset position.

    Args:
        foreground_artifact_id: Artifact ID of the foreground image (e.g., product with transparent bg).
        background_artifact_id: Artifact ID of the background image.
        position: Where to place the foreground. Options: "center", "center-top", "center-bottom",
                  "left-center", "right-center", "top-left", "top-right", "bottom-left", "bottom-right".
                  Defaults to "center".
        scale: Scale factor for the foreground relative to the background height.
               0.5 = foreground is 50% of background height. 0.8 = 80%. 1.0 = same height.
               Defaults to 1.0.
        x_offset: Horizontal pixel offset from the position preset. Positive = right, negative = left.
        y_offset: Vertical pixel offset from the position preset. Positive = down, negative = up.

    Returns:
        dict with image dimensions and artifact info so you can make informed adjustments.
    """
    try:
        fg_artifact = await tool_context.load_artifact(filename=foreground_artifact_id)
        bg_artifact = await tool_context.load_artifact(filename=background_artifact_id)

        if fg_artifact is None:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "message": f"Foreground artifact {foreground_artifact_id} not found",
            }
        if bg_artifact is None:
            return {
                "status": "error",
                "tool_response_artifact_id": "",
                "message": f"Background artifact {background_artifact_id} not found",
            }

        # Load images
        fg_image = Image.open(BytesIO(fg_artifact.inline_data.data)).convert("RGBA")
        bg_image = Image.open(BytesIO(bg_artifact.inline_data.data)).convert("RGBA")

        orig_fg_w, orig_fg_h = fg_image.size
        bg_w, bg_h = bg_image.size

        # Scale foreground relative to background height
        if scale != 1.0:
            target_h = int(bg_h * scale)
            aspect = orig_fg_w / orig_fg_h
            target_w = int(target_h * aspect)
            fg_image = fg_image.resize((target_w, target_h), Image.LANCZOS)

        fg_w, fg_h = fg_image.size

        # Calculate position from preset
        if position not in POSITION_PRESETS:
            position = "center"
        x, y = _calculate_position(position, fg_w, fg_h, bg_w, bg_h)

        # Apply offset
        x += x_offset
        y += y_offset

        # Composite
        result = bg_image.copy()
        result.paste(fg_image, (x, y), fg_image)

        # Save
        output_buffer = BytesIO()
        result.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()

        result_id = f"comp_{tool_context.function_call_id}.png"
        result_part = Part(inline_data={"mime_type": "image/png", "data": output_bytes})
        await tool_context.save_artifact(filename=result_id, artifact=result_part)

        return {
            "status": "success",
            "tool_response_artifact_id": result_id,
            "foreground_artifact_id": foreground_artifact_id,
            "background_artifact_id": background_artifact_id,
            "background_dimensions": f"{bg_w}x{bg_h}",
            "foreground_original_dimensions": f"{orig_fg_w}x{orig_fg_h}",
            "foreground_scaled_dimensions": f"{fg_w}x{fg_h}",
            "placed_at": f"({x}, {y})",
            "position_preset": position,
            "scale": str(scale),
            "message": f"Foreground ({fg_w}x{fg_h}) placed at ({x}, {y}) on background ({bg_w}x{bg_h}) using position='{position}', scale={scale}",
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
