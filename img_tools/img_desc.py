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
PROMPT = """
Act as an expert image captioner for AI training. Describe the attached image of the woman, whom we will call ohmyra, in a single, highly detailed paragraph.

Instructions:

Start with the Trigger: Begin the description with the word ohmyra.

Exclude Facial Features: Do not describe her eye color, nose shape, lip shape, or specific facial structure. These are the permanent traits we want to bake into the trigger word.

Describe Hair as a Variable: Since her hair changes, you must describe her hairstyle, color, and length in this specific image (e.g., 'long wavy hair let down,' 'hair tied in a messy bun,' or 'straight hair tucked behind ears').

Shot & Composition: State the shot type (close-up, medium shot, or full-body) and the camera perspective.

Clothing & Accessories: Detail the outfit, including fabrics, colors, and any jewelry.

Pose & Expression: Describe her body orientation and her facial expression (e.g., 'smiling,' 'pouty,' 'serious,' 'laughing').

Environment & Lighting: Detail the background, lighting quality (e.g., 'golden hour,' 'harsh flash,' 'dim interior'), and color palette.

Technical Quality: Note the depth of field and focus (e.g., 'blurred background,' 'sharp focus throughout').

Constraints:

DO NOT use the words 'woman' or 'girl'; use the trigger word ohmyra.

DO NOT use flowery language. Be literal and objective.

START the response directly with 'ohmyra'."

Example Output for your Script:
"ohmyra, a medium shot from a side angle, wearing a blue denim jacket over a white t-shirt. Her hair is tied back in a sleek ponytail. She is looking off-camera with a contemplative expression. The setting is a sun-drenched urban park with blurred trees and a park bench in the background. The lighting is warm and natural with soft shadows on her shoulder.
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
    img = get_base64_image(image_path)
    image_url = f"data:image/png;base64,{img}"

    message = HumanMessage(
        content=[
            {"type": "text", "text": PROMPT},
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

        image_path = os.path.join(image_dir, image)
        caption_path = os.path.join(image_dir, name + ".txt")

        if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            print(f"Skipping {image} (unsupported format)")
            continue

        if os.path.exists(caption_path):
            try:
                if os.path.getsize(caption_path) > 0:
                    print(f"Skipping {image_path} (caption exists)")
                    continue
            except OSError:
                pass

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


def caption_single_image(model, image_path):
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

    print("Captioning image: ", image_path)
    start = time.perf_counter()
    try:
        caption = caption_img(model, image_path)
    finally:
        print("Time taken: ", time.perf_counter() - start)

    print("Writing caption to file: ", caption_path)
    with open(caption_path, "w") as f:
        f.write(caption)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    _set_env("GOOGLE_API_KEY")
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
    )

    if os.path.isdir(args.path):
        caption_image_dataset(model, args.path)
    else:
        caption_single_image(model, args.path)


if __name__ == "__main__":
    main()
