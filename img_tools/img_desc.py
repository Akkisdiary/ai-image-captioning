import getpass
import io
import os
import base64
import time

from dotenv import load_dotenv
from PIL import Image
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


def _set_env(var: str):
    load_dotenv()
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


_set_env("GOOGLE_API_KEY")


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROMPT_2 = """
You are an expert at creating complete image generation prompts for Seedream 4.0 AI model.

IMPORTANT CONTEXT:
- Seedream will receive 2 reference images in this order:
  1. Images 1: Face structure, body type and physique references
  2. Image 2: THIS image - complete scene reference
- You are analyzing image 2 ONLY
- Your output must be a COMPLETE prompt for Seedream

YOUR TASK:
Analyze this image and create a complete Seedream prompt that instructs the AI how to use all references and describes everything visible in THIS image.

OUTPUT FORMAT (mandatory structure):

"Use the first reference image for the face structure, body type and physique. Use reference image 2 as the complete reference for clothing, pose, action, scene composition, background environment, lighting setup, and overall atmosphere.

Subject details: [Describe the person's clothing in complete detail - every garment, accessories, jewelry, shoes, specific details like patterns, textures, colors, cuts, styles]. [Describe the exact pose - standing, sitting, body position, arm placement, leg position]. [Describe what the person is doing - their action, gesture, body language, facial expression like smiling/serious but WITHOUT describing facial features].

The scene: [describe location type and setting]. The environment features [describe architectural elements, furniture, props, and background in detail]. The setting is [indoor/outdoor details with spatial relationships].

Lighting: [describe light source, direction, quality, shadows, time of day, color temperature in technical detail].

Camera: [describe angle, perspective, depth of field, focal distance, composition].

Atmosphere: [describe mood, ambiance, weather if applicable, environmental effects].

Colors and textures: [describe dominant colors throughout the scene, materials, surface properties, color palette].

Technical quality: [high-resolution, sharp focus, professional photography, etc.]."

CRITICAL RULES:
- DO describe: clothing (every detail), pose, action, body language, gesture, expression type (smile/serious)
- NEVER describe: hair color, hair style, eye color, facial features, skin tone, ethnic features
- Use "this person", "the subject" when referring to the individual
- Be extremely detailed about clothing and accessories
- Be precise about pose and body position
- Focus on EVERYTHING visible except facial/hair features

Output ONLY the formatted prompt, nothing else.
"""


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


def caption_img(model, image_path):
    prompt = """
    Describe this image in great detail in the following section for
    character LORA training.

    1. Subject, pose, facial expressions
    2. Background
    3. Camera angle & details
    4. Lighting

    Provide a single cohesive paragraph for each section separately.
    The output should not contain any titles, headers, filler text,
    or surrounding text.
    """
    print(f"captioning image: {image_path}")
    img = get_base64_image(image_path)
    image_url = f"data:image/png;base64,{img}"

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    )
    response = model.invoke([message])
    return response.content


def caption_image_dataset(model, image_dir):
    if not os.path.exists(image_dir):
        raise ValueError(f"Image directory {image_dir} does not exist")

    for image in os.listdir(image_dir):
        name, ext = os.path.splitext(image)
        ext = ext.lower()

        if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            print(f"Skipping {image}")
            continue

        image_path = os.path.join(image_dir, image)
        caption_path = os.path.join(image_dir, name + ".txt")

        print("Captioning image: ", image_path)
        start = time.perf_counter()

        try:
            caption = caption_img(model, image_path)
        except Exception as e:
            print(f"Unable to caption image {image_path}, {e}")
            continue
        finally:
            print("Time taken: ", time.perf_counter() - start)

        print("Writing caption to file: ", caption_path)
        with open(caption_path, "w") as f:
            f.write(caption)


def main():
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
    )

    dataset_dir = os.path.join(BASE_DIR, "data")
    caption_image_dataset(model, dataset_dir)


if __name__ == "__main__":
    main()
