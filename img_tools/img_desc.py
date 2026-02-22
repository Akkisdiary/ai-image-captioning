import getpass
import io
import os
import base64
import time
import argparse

from dotenv import load_dotenv
from PIL import Image
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


def _set_env(var: str):
    load_dotenv()
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROMPT_LORA = """
# Role
Act as an expert Image Captioner and Vision Analyst. Your goal is to provide a dense, literal, and technical description of the attached image for AI model training (LoRA).

# Task
Analyze the image and describe the subject, "{trigger_word}," with extreme precision. 

# Formatting Rules
1. **The Trigger:** The very first word of your entire response must be "{trigger_word}".
2. **Subject Identity:** Use the name "{trigger_word}" exclusively. Never use "woman," "girl," or "model."
3. **The "No-Face" Rule:** Do NOT describe her eyes (color/shape), nose, or lips. These are permanent traits of "{trigger_word}." 
4. **Detailed Hair (Variable):** Since hair changes, describe the color, length, texture (frizzy, silky, wavy), and specific styling (tucked, parted, tied).
5. **Makeup & Skin (Variable):** Detail the makeup style (matte, dewy, winged eyeliner, bold red lipstick, natural) and skin texture (freckles, tanned, pale, oily, matte).
6. **Anatomical Pose:** Describe the exact orientation of her body. Mention the tilt of the head, the position of the shoulders, and where her hands/arms are placed (e.g., "head tilted 15 degrees left, right hand resting on chin, shoulders slumped").

# Technical Hierarchy (The Order of Description)
* **Trigger:** {trigger_word}
* **Shot & Perspective:** (e.g., "Extreme close-up, low-angle shot, side profile")
* **Expression:** (e.g., "Neutral, smiling, mouth slightly agape, squinting")
* **Pose:** (Specific body and limb positioning)
* **Makeup:** (Specific products, colors, and skin finish)
* **Hair:** (Color, style, and flow)
* **Clothing/Accessories:** (Fabrics like silk, denim, or lace; jewelry; eyewear)
* **Environment:** (Background elements, depth of field, location)
* **Lighting/Color:** (Color temperature, light source direction, shadows)

# Constraints
* Use **Literal Language:** Avoid "beautiful," "stunning," or "graceful." Use "symmetrical," "vibrant," or "upright."
* **No Introduction:** Do not say "Here is the description..." or "This image shows..." 
* **Single Paragraph:** Deliver the entire description in one continuous, dense paragraph.

# Start your response with "{trigger_word}"
"""

PROMPT_AMATEUR_EDIT = """
# SYSTEM PROMPT: VISION-TO-EDITING PROMPT GENERATOR (VERSION 2.0)

## ROLE
You are an expert Image Analyst and Prompt Engineer. Your task is to analyze an input Image (A) and generate a highly detailed "Image Editing Prompt." This generated prompt will be used to transplant a new subject (Image B) into the specific scene, lighting, and composition found in Image (A).

## CORE OBJECTIVE
Generate a descriptive prompt that achieves "Absolute Realism." The output must describe a high-quality, intimate, amateur smartphone-style photograph (Instagram/Pinterest aesthetic). Focus on raw, unpolished, and life-like details while strictly avoiding "cinematic" or "professional studio" descriptors.

## MANDATORY PROMPT ELEMENTS
Every prompt you generate must integrate these four pillars:

### 1. Subject Identity & Preservation
- **Identity Guard:** Explicitly state: "Preserve the provided subject's exact face, natural likeness, unique facial structure, and identity perfectly."
- **Natural Texture:** Demand "visible skin pores, fine lines, tiny blemishes, peach fuzz, and realistic hydration shine." Forbid "AI-smoothing" or "beautification."

### 2. Pose, Clothing & Accessories (The "Look")
- **Pose & Eye Contact:** Describe the subject's body orientation (e.g., "turned 45 degrees," "slumped casually"), head tilt, and where they are looking (e.g., "direct, relaxed gaze into the lens").
- **Hair style:** Describe the subject's hair (e.g., "long wavy hair let down," "hair tied in a messy bun," or "straight hair tucked behind ears").
- **Wardrobe Detail:** Describe the clothing materials and fit (e.g., "ribbed cotton tank top," "oversized knit sweater with pilling," "wrinkled linen shirt").
- **Accessories:** Note any jewelry, glasses, or hair accessories (e.g., "thin gold hoop earrings," "a messy claw clip with stray hairs," "smudged wire-rimmed glasses").

### 3. Amateur Smartphone Aesthetic
- **Camera Style:** Use keywords: "Captured on a smartphone," "Amateur lifestyle photography," "Candid snapshot," "Instagram-style POV," "Natural sensor grain."
- **Lighting:** Describe lighting as "mixed artificial glow," "harsh overhead light," or "natural side-window light." Forbid "softboxes" or "rim lighting."
- **Focus:** Ensure a natural, deep focus rather than artificial professional bokeh. The background should be clear and realistic, not a "dreamy" blur.

### 4. Environmental Context & Composition
- **Background Details:** Describe the background in detail (e.g., "cluttered wooden table," "busy open kitchen," "fluorescent-lit grocery aisle").
- **Compositional Balance:** Mention specific props (e.g., "condensation on a glass," "half-eaten plate," "stray napkins") and their position relative to the subject.

## STYLISTIC NEVERS (NEGATIVE CONSTRAINTS)
- **DO NOT use:** "Cinematic," "Dramatic lighting," "8k," "Masterpiece," "Blurry background," "Shallow depth of field," "Professional portrait," "Studio-lit."
- **Avoid:** Any language implying a high-end DSLR or a professional photographer's intervention.

## OUTPUT FORMAT
Provide the final prompt string, starting with the instruction: 
"Using the reference image of the subject, create a..."
"""


def get_chat_gemini():
    _set_env("GOOGLE_API_KEY")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
    )


def get_image_bytes(image_path):
    # image_format = image_path.split(".")[-1].lower()
    image = Image.open(image_path)

    with io.BytesIO() as output:
        image.save(output, format="png")
        image_bytes = output.getvalue()
    return image_bytes


def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def caption_image(model, image_path):
    if not os.path.exists(image_path):
        raise ValueError(f"Image path {image_path} does not exist")

    if not os.path.isfile(image_path):
        raise ValueError(f"Image path {image_path} is not a file")

    name, ext = os.path.splitext(os.path.basename(image_path))
    ext = ext.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise ValueError(f"Unsupported image extension: {ext}")

    caption_path = os.path.join(os.path.dirname(image_path), name + ".txt")
    if os.path.exists(caption_path):
        try:
            if os.path.getsize(caption_path) > 0:
                print(f"Skipping {image_path} (caption exists)")
                return
        except OSError:
            pass

    start = time.perf_counter()
    try:
        print("Captioning image:", image_path)
        prompt = PROMPT_LORA.replace("{trigger_word}", "ohmyra")
        img = get_base64_image(image_path)
        image_b64 = f"data:image/png;base64,{img}"
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_b64}},
            ]
        )
        response = model.invoke([message])
        caption = response.content
    finally:
        print("Time taken:", time.perf_counter() - start)

    print("Writing caption to file:", caption_path)
    with open(caption_path, "w") as f:
        f.write(caption)


def caption_image_dataset(model, image_dir):
    if not os.path.exists(image_dir):
        raise ValueError(f"Image directory {image_dir} does not exist")

    for file in os.listdir(image_dir):
        try:
            caption_image(model, os.path.join(image_dir, file))
        except Exception as e:
            print(f"Unable to caption image {file}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    model = get_chat_gemini()

    if os.path.isdir(args.path):
        caption_image_dataset(model, args.path)
    else:
        caption_image(model, args.path)


if __name__ == "__main__":
    main()
