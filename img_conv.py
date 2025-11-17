from PIL import Image
import os


def convert_webp_to_png(input_path, output_path):
    """
    Converts a WebP image to PNG format.

    Args:
        input_path (str): The path to the input WebP image file.
        output_path (str): The path where the output PNG image will be saved.
    """
    try:
        # Open the WebP image
        img = Image.open(input_path)

        # Save the image as PNG. Pillow automatically handles the conversion
        # and preserves transparency if present in the WebP.
        img.save(output_path, "PNG")
        print(f"Successfully converted '{input_path}' to '{output_path}'")
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
    except Exception as e:
        print(f"An error occurred during conversion: {e}")


def convert_webp_to_png_bulk(input_folder, output_folder):
    for img in os.listdir(input_folder):
        name, ext = os.path.splitext(img)
        ext = ext.lower()

        if ext not in [".webp"]:
            print(f"Skipping {img}")
            continue

        image = Image.open(os.path.join(input_folder, img))
        image.save(os.path.join(output_folder, name + ".png"))


if __name__ == "__main__":
    input_webp_file = "/Users/ashegaonkar/passionsfruit/ai-characters/umanorth"

    convert_webp_to_png_bulk(input_webp_file, input_webp_file)
