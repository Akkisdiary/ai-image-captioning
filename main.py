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
        caption = caption_img(model, image_path)
        print("Time taken: ", time.perf_counter() - start)

        print("Writing caption to file: ", caption_path)
        with open(caption_path, "w") as f:
            f.write(caption)


def main():
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY")
    )

    dataset_dir = os.path.join(BASE_DIR, "data")
    caption_image_dataset(model, dataset_dir)


if __name__ == "__main__":
    main()
