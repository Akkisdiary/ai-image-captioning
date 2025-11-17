#!/usr/bin/env python3
"""
Script to modify EXIF metadata of images based on sample data.
Supports JPEG, PNG, and other PIL-compatible formats.
"""

import os
import random
import sys
from datetime import datetime, timedelta

import numpy as np
import piexif
from PIL import Image, ImageEnhance


def generate_content_filename(is_video=False):
    """Generate a random iPhone-style filename for content"""
    # Various filename formats
    if random.random() < 0.7:  # 70% classic format
        number = random.randint(1000, 9999)
        prefix = (
            random.choice(["IMG_", "VID_", "VIDEO_", "CLIP_", "REC_", "MOV_"])
            if is_video
            else random.choice(["IMG_", "PHOTO_", "PIC_", "SHOT_"])
        )
        extension = ".MP4" if is_video else ".JPG"
        return f"{prefix}{number}{extension}"
    else:  # 30% timestamp format
        now = datetime.now()
        random_days = random.randint(-90, 0)
        random_hours = random.randint(0, 23)
        random_mins = random.randint(0, 59)
        random_secs = random.randint(0, 59)

        random_date = now + timedelta(
            days=random_days,
            hours=random_hours,
            minutes=random_mins,
            seconds=random_secs,
        )
        date_str = random_date.strftime("%Y%m%d")
        time_str = random_date.strftime("%H%M%S")

        prefix = (
            random.choice(["IMG_", "VID_", "VIDEO_", "CLIP_", "REC_", "MOV_"])
            if is_video
            else random.choice(["IMG_", "PHOTO_", "PIC_", "SHOT_"])
        )
        extension = ".MP4" if is_video else ".JPG"

        if random.random() < 0.5:
            return f"{prefix}{date_str}_{time_str}{extension}"
        else:
            return f"{prefix}{date_str}{time_str}{extension}"


def repurpose_image(input_path):
    """Process an image with subtle changes to avoid detection"""
    # Generate a random filename
    base_dir = os.path.dirname(input_path)
    iphone_filename = generate_content_filename(is_video=False)
    output_path = os.path.join(base_dir, iphone_filename)

    # Open the image file
    img = Image.open(input_path)

    # Randomly apply subtle modifications
    modifications_applied = []

    # Random slight rotation (0.1-0.5 degrees)
    if random.random() < 0.6:
        rotation_angle = random.uniform(-0.5, 0.5)
        img = img.rotate(rotation_angle, resample=Image.BICUBIC, expand=False)
        modifications_applied.append(f"Subtle rotation: {rotation_angle:.2f}°")

    # Random subtle crop (0.5-1.0%)
    if random.random() < 0.7:
        width, height = img.size
        crop_percent = random.uniform(0.005, 0.01)
        crop_pixels_x = int(width * crop_percent)
        crop_pixels_y = int(height * crop_percent)

        left = random.randint(0, crop_pixels_x)
        top = random.randint(0, crop_pixels_y)
        right = width - random.randint(0, crop_pixels_x)
        bottom = height - random.randint(0, crop_pixels_y)

        img = img.crop((left, top, right, bottom))
        img = img.resize((width, height), Image.LANCZOS)
        modifications_applied.append(f"Subtle crop and resize: {crop_percent*100:.2f}%")

    # Random subtle brightness adjustment
    if random.random() < 0.6:
        brightness_factor = random.uniform(0.97, 1.03)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_factor)
        modifications_applied.append(f"Brightness adjustment: {brightness_factor:.2f}")

    # Random subtle contrast adjustment
    if random.random() < 0.5:
        contrast_factor = random.uniform(0.98, 1.02)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)
        modifications_applied.append(f"Contrast adjustment: {contrast_factor:.2f}")

    # Random subtle color adjustment
    if random.random() < 0.5:
        color_factor = random.uniform(0.98, 1.02)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(color_factor)
        modifications_applied.append(f"Color adjustment: {color_factor:.2f}")

    # Add very subtle noise
    if random.random() < 0.4:
        img_array = np.array(img)
        # Clamp noise level to safe range
        noise_level = max(0.5, min(2.0, random.uniform(0.5, 2.0)))
        noise = np.random.normal(0, noise_level, img_array.shape).astype(np.uint8)
        noisy_img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(noisy_img_array)
        modifications_applied.append(f"Subtle noise: {noise_level:.2f}")

    # Create EXIF data dictionary
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

    # Random creation date (1-120 days ago)
    now = datetime.now()
    random_days = random.randint(1, 120)
    random_date = now - timedelta(days=random_days)
    date_time_str = random_date.strftime("%Y:%m:%d %H:%M:%S")

    # Set EXIF data
    exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_str.encode("utf-8")
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_time_str.encode("utf-8")
    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_time_str.encode("utf-8")
    exif_dict["0th"][piexif.ImageIFD.Make] = "Apple".encode("utf-8")
    exif_dict["0th"][piexif.ImageIFD.Model] = (
        f"iPhone {random.choice(['11', '12', '13', '14', '15'])} Pro".encode("utf-8")
    )
    exif_dict["0th"][piexif.ImageIFD.Software] = (
        f"iOS {random.randint(14, 17)}.{random.randint(0, 6)}".encode("utf-8")
    )

    # Random GPS info (if original had it) - about 30% chance
    if random.random() < 0.3:
        # Random coordinates (very generic - middle of oceans, etc.)
        lat = random.uniform(-60, 60)
        lon = random.uniform(-160, 160)

        # Convert to EXIF format
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"
        lat = abs(lat)
        lon = abs(lon)

        lat_deg = int(lat)
        lat_min = int((lat - lat_deg) * 60)
        lat_sec = int(((lat - lat_deg) * 60 - lat_min) * 60)

        lon_deg = int(lon)
        lon_min = int((lon - lon_deg) * 60)
        lon_sec = int(((lon - lon_deg) * 60 - lon_min) * 60)

        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref.encode("utf-8")
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = (
            (lat_deg, 1),
            (lat_min, 1),
            (lat_sec, 1),
        )
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref.encode("utf-8")
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = (
            (lon_deg, 1),
            (lon_min, 1),
            (lon_sec, 1),
        )
        exif_dict["GPS"][piexif.GPSIFD.GPSDateStamp] = date_time_str.encode("utf-8")

        modifications_applied.append("Added generic geolocation data")

    exif_dict.pop("GPS", None)
    # Convert EXIF to bytes
    exif_bytes = piexif.dump(exif_dict)

    # Save the modified image with EXIF data
    img.save(output_path, quality=95, exif=exif_bytes)

    # Verify the image was saved successfully
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        return False

    return True


def main():
    """
    Main function to handle command-line arguments.
    """
    if len(sys.argv) < 2:
        print("Usage: python img_exif.py <image_path> [output_path]")
        print("")
        print("Examples:")
        print("  python img_exif.py photo.jpg")
        print("  python img_exif.py photo.png photo_modified.jpg")
        print("")
        print("If output_path is not provided, the original file will be overwritten.")
        sys.exit(1)

    input_path = sys.argv[1]

    success = repurpose_image(input_path)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
