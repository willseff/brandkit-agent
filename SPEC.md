# BrandKit Agent — Spec

A single LlmAgent (Google ADK) that iteratively edits product images through multi-step tool chains. The agent sees intermediate results via artifact injection and self-corrects until satisfied.

## Core Architecture

- One `LlmAgent` (`gemini-2.5-flash`) as the root agent — plans, calls tools, inspects results, loops
- `before_model_callback` for multimodal context injection (user uploads + tool response images)
- Artifact-based image passing between tools (artifact ID strings, not raw bytes)
- All tools follow the pattern: **artifact ID in → process → artifact ID out**
- Agent naturally loops: calls tool → sees result → decides to call again or respond

## Tools

### 1. `generate_image`
- **What:** Text prompt → new image
- **Model:** Nano Banana 2 (`gemini-3.1-flash-image-preview`)
- **Params:** `prompt: str`, `aspect_ratio: str = "1:1"`
- **Returns:** `{ status, tool_response_artifact_id }`

### 2. `generate_image_with_reference`
- **What:** Text prompt + reference image(s) → new image guided by references
- **Model:** Nano Banana 2 (`gemini-3.1-flash-image-preview`)
- **Params:** `prompt: str`, `reference_artifact_ids: list[str]`, `aspect_ratio: str = "1:1"`
- **Returns:** `{ status, tool_response_artifact_id }`
- **Use cases:** Subject consistency, style transfer, "make something like this but..."
- **Note:** Supports up to 14 reference images per request

### 3. `edit_image`
- **What:** Existing image + text prompt → edited image
- **Model:** Nano Banana 2 (`gemini-3.1-flash-image-preview`)
- **Params:** `image_artifact_id: str`, `edit_prompt: str`
- **Returns:** `{ status, tool_response_artifact_id, edit_prompt }`
- **Use cases:** Change background, adjust lighting, add props, reposition

### 4. `remove_background`
- **What:** Image → image with transparent background
- **Library:** `rembg`
- **Params:** `image_artifact_id: str`
- **Returns:** `{ status, tool_response_artifact_id }`

### 5. `composite_images`
- **What:** Layer multiple images together (foreground on background)
- **Library:** `Pillow`
- **Params:** `foreground_artifact_id: str`, `background_artifact_id: str`, `x: int = 0`, `y: int = 0`, `scale: float = 1.0`
- **Returns:** `{ status, tool_response_artifact_id }`

### 6. `overlay_text`
- **What:** Render text onto an image
- **Library:** `Pillow`
- **Params:** `image_artifact_id: str`, `text: str`, `x: int`, `y: int`, `font_size: int = 40`, `color: str = "#FFFFFF"`, `font: str = "default"`
- **Returns:** `{ status, tool_response_artifact_id }`

## Example Workflows

### Product on custom background
1. `remove_background(user_muffin.png)` → `nobg_1.png`
2. `generate_image("marble countertop in bright kitchen")` → `bg_2.png`
3. `composite_images(foreground=nobg_1.png, background=bg_2.png)` → `comp_3.png`
4. `edit_image(comp_3.png, "add warm natural light from left")` → `final_4.png`

### Branded product mockup
1. `edit_image(product.png, "clean white background")` → `clean_1.png`
2. `overlay_text(clean_1.png, "ACME Co.", x=50, y=30, font_size=60)` → `branded_2.png`

### Style-consistent product line
1. User uploads `hero_product.png`
2. `generate_image_with_reference("same style photo of blue version", [hero_product.png])` → `blue_1.png`
3. `generate_image_with_reference("same style photo of red version", [hero_product.png])` → `red_2.png`

## Key Mechanisms

- **`before_model_callback`**: Intercepts `inline_data` (user uploads) and `function_response` (tool outputs) to inject actual image bytes into LLM context so the agent can see what it's working with
- **Artifact IDs**: Hash-based for user uploads (`usr_upl_img_<hash>.png`), function_call_id-based for tool outputs (`<tool>_<id>.png`)
- **Artifact store**: ADK's built-in `tool_context.save_artifact()` / `load_artifact()`

## Dependencies

- `google-adk` — agent framework
- `google-genai` — Gemini API (Nano Banana 2 for generation/editing)
- `Pillow` — image compositing + text overlay
- `rembg` — background removal

## File Structure

```
brandkit_agent/
├── __init__.py
├── .env                    # GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI
├── agent.py                # root_agent definition
├── prompt.py               # system instruction
├── callbacks.py            # before_model_callback (user uploads + tool response image injection)
└── tools/
    ├── __init__.py
    ├── generate.py         # generate_image
    ├── generate_ref.py     # generate_image_with_reference
    ├── edit.py             # edit_image
    ├── background.py       # remove_background
    ├── composite.py        # composite_images
    └── text_overlay.py     # overlay_text
```

## Models

| Model | Code | Use |
|-------|------|-----|
| Nano Banana 2 | `gemini-3.1-flash-image-preview` | Image generation + editing (tools) |
| Gemini 2.5 Flash | `gemini-2.5-flash` | Agent orchestration LLM |
