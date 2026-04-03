from google.adk.tools import ToolContext
from PIL import Image
from io import BytesIO
import logging


async def get_image_dimensions(
    tool_context: ToolContext,
    image_artifact_id: str,
) -> dict[str, str]:
    """Get the dimensions (width and height in pixels) of an image artifact.

    IMPORTANT: Always call this before composite_images to understand the sizes
    of both foreground and background images. This lets you pick the right
    scale and position so the foreground isn't cropped or misplaced.

    Args:
        image_artifact_id: Artifact ID of the image to measure.

    Returns:
        dict with width, height, and aspect ratio info.
    """
    try:
        artifact = await tool_context.load_artifact(filename=image_artifact_id)
        if artifact is None:
            return {
                "status": "error",
                "message": f"Artifact {image_artifact_id} not found",
            }

        image = Image.open(BytesIO(artifact.inline_data.data))
        w, h = image.size

        return {
            "status": "success",
            "image_artifact_id": image_artifact_id,
            "width": str(w),
            "height": str(h),
            "dimensions": f"{w}x{h}",
            "aspect_ratio": f"{w/h:.2f}",
            "message": f"Image is {w}x{h} pixels (aspect ratio {w/h:.2f})",
        }
    except Exception as e:
        logging.error(e)
        return {
            "status": "error",
            "message": f"Error reading image dimensions: {str(e)}",
        }
