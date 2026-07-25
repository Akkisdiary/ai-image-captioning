import argparse
from pathlib import Path

from ai import get_vision_response
from constants import IMG_SUFFIXES
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.chat_models import init_chat_model
from utils import (
    read_file,
    read_image,
    resolve_dataset_path,
    resolve_prompt_path,
)
from constants import BASE_DIR

load_dotenv()


class PromptExistsException(Exception):
    pass


def gen_file(
    model: BaseChatModel,
    img_path: Path,
    prompt_path: Path,
    trigger_word: str | None = None,
):
    print(f"Generating prompt for file: {img_path}")
    try:

        if not img_path.exists():
            print(f"File does not exists {img_path}")
            return

        if not img_path.is_file():
            print(f"Not a file {img_path}")
            return

        out_path = img_path.with_suffix(".txt")

        if (
            out_path.exists()
            and out_path.is_file()
            and out_path.stat().st_size > 0
        ):
            raise PromptExistsException(f"Prompt exists, skipping {out_path}")

        img_b64 = read_image(img_path)
        prompt_str = read_file(prompt_path)

        if isinstance(trigger_word, str):
            prompt_str = prompt_str.replace("{trigger_word}", trigger_word)

        full_text = get_vision_response(model, img_b64, prompt_str)

        with open(out_path, "w") as f:
            f.write(full_text)

        print(f"Prompt generated {out_path}")
    except PromptExistsException as e:
        print(e)


def gen_folder(
    model: BaseChatModel,
    folder_path: Path,
    prompt_path: Path,
    trigger_word: str | None = None,
):
    print(f"Generating prompts for folder: {folder_path}")

    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")

    success = failed = skipped = 0

    try:
        for file in folder_path.iterdir():
            if not file.exists() or not file.is_file():
                continue
            if file.suffix not in IMG_SUFFIXES:
                print(f"Not an image: {file}")
                continue
            try:
                gen_file(model, file, prompt_path, trigger_word)
                success += 1
            except PromptExistsException as e:
                skipped += 1
                print(e)
            except Exception as e:
                print(f"Unable to gen prompt: {file}\n{e}")
                failed += 1
    except KeyboardInterrupt:
        print("KeyboardInterrupt: stopping")
        print()

    print(f"{success=}")
    print(f"{failed=}")
    print(f"{skipped=}")


def get_prompt_choices():
    prompts_dir = Path(BASE_DIR) / "prompts"
    return [
        f.name
        for f in prompts_dir.iterdir()
        if f.is_file() and f.suffix in (".md", ".MD")
    ]


def main():
    prompt_choices = get_prompt_choices()
    model_choices = [
        "google_genai:gemini-2.5-flash",
        "ollama:gemma4-128k:latest",
    ]
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path")
    parser.add_argument(
        "--prompt-path",
        default="CHAR_LORA.md",
        required=False,
        choices=prompt_choices,
    )
    parser.add_argument(
        "--trigger-word",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--model",
        default="google_genai:gemini-2.5-flash",
        required=False,
        choices=model_choices,
    )
    args = parser.parse_args()

    data_path = resolve_dataset_path(args.data_path)
    prompt_path = resolve_prompt_path(args.prompt_path)
    trigger_word = args.trigger_word
    model = args.model

    print("=" * 80)
    print(f"data_path: {str(data_path)}")
    print(f"prompt_path: {str(prompt_path)}")
    print(f"trigger_word: {trigger_word}")
    print(f"model: {model}")
    print("=" * 80)
    print()

    model = init_chat_model(model=model, temperature=0.4)

    if data_path.is_dir():
        gen_folder(model, data_path, prompt_path, trigger_word)
    else:
        gen_file(model, data_path, prompt_path, trigger_word)


if __name__ == "__main__":
    main()
