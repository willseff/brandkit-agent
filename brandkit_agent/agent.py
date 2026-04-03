from google.adk.agents import LlmAgent

from .prompt import AGENT_INSTRUCTION
from .callbacks import before_model_modifier
from .tools import (
    generate_image,
    generate_image_with_reference,
    edit_image,
    remove_background,
    composite_images,
    overlay_text,
    get_image_dimensions,
)

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="brandkit_agent",
    instruction=AGENT_INSTRUCTION,
    tools=[
        generate_image,
        generate_image_with_reference,
        edit_image,
        remove_background,
        composite_images,
        overlay_text,
        get_image_dimensions,
    ],
    before_model_callback=before_model_modifier,
)
