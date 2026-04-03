from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai.types import Part
import hashlib
from typing import List

# Tool names that produce image artifacts
IMAGE_PRODUCING_TOOLS = [
    "generate_image",
    "generate_image_with_reference",
    "edit_image",
    "remove_background",
    "composite_images",
    "overlay_text",
]


async def before_model_modifier(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Modify LLM request to include artifact references for images."""
    for content in llm_request.contents:
        if not content.parts:
            continue

        modified_parts = []
        for part in content.parts:
            if part.inline_data:
                processed_parts = await _process_inline_data_part(
                    part, callback_context
                )
            elif part.function_response:
                if part.function_response.name in IMAGE_PRODUCING_TOOLS:
                    processed_parts = await _process_function_response_part(
                        part, callback_context
                    )
                else:
                    processed_parts = [part]
            else:
                processed_parts = [part]

            modified_parts.extend(processed_parts)

        content.parts = modified_parts


async def _process_inline_data_part(
    part: Part, callback_context: CallbackContext
) -> List[Part]:
    """Process inline data parts (user-uploaded images)."""
    artifact_id = _generate_artifact_id(part)

    if artifact_id not in await callback_context.list_artifacts():
        await callback_context.save_artifact(filename=artifact_id, artifact=part)

    return [
        Part(
            text=f"[User Uploaded Artifact] Below is the content of artifact ID : {artifact_id}"
        ),
        part,
    ]


def _generate_artifact_id(part: Part) -> str:
    """Generate a unique artifact ID for user uploaded image."""
    filename = part.inline_data.display_name or "uploaded_image"
    image_data = part.inline_data.data

    hash_input = filename.encode("utf-8") + image_data
    content_hash = hashlib.sha256(hash_input).hexdigest()[:16]

    mime_type = part.inline_data.mime_type
    extension = mime_type.split("/")[-1]

    return f"usr_upl_img_{content_hash}.{extension}"


async def _process_function_response_part(
    part: Part, callback_context: CallbackContext
) -> List[Part]:
    """Process function response parts and append artifacts."""
    artifact_id = part.function_response.response.get("tool_response_artifact_id")

    if not artifact_id:
        return [part]

    artifact = await callback_context.load_artifact(filename=artifact_id)

    return [
        part,
        Part(
            text=f"[Tool Response Artifact] Below is the content of artifact ID : {artifact_id}"
        ),
        artifact,
    ]
