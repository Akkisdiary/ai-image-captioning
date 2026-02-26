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


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _set_env(var: str):
    load_dotenv()
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


def get_chat_gemini():
    _set_env("GOOGLE_API_KEY")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
    )


def read_prompt(prompt_path: str):
    with open(prompt_path, "r") as f:
        return f.read()


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
        prompt = read_prompt(os.path.join(BASE_DIR, "prompts", "LORA.md"))
        prompt = prompt.replace("{trigger_word}", "ohmyra")
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
