#!/usr/bin/env python3
"""
Script to modify EXIF metadata of images based on sample data.
Supports JPEG, PNG, and other PIL-compatible formats.
"""

import piexif
from PIL import Image
import sys
import os
from datetime import datetime, timedelta
import random
import cv2
import numpy as np


def analyze_image(img):
    """
    Analyze image to extract measurable properties.
    Returns a dictionary with calculated values.

    Args:
        img: PIL Image object
    """
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]

    analysis = {
        "width": width,
        "height": height,
        "orientation": 1,  # Default: normal
        "brightness": 0.0,
        "color_temp": 5000,
        "has_flash": False,
    }

    # Set orientation to normal (1) - image is already correctly oriented
    # EXIF orientation 1 means no rotation needed
    analysis["orientation"] = 1

    # Calculate brightness (average luminance)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    # Convert to EXIF brightness value (APEX scale)
    # APEX brightness = log2(B) where B is luminance
    # Normalize to -5 to +10 range
    analysis["brightness"] = (avg_brightness / 255.0) * 15 - 5

    # Estimate color temperature
    # Calculate average R, G, B values
    avg_color = np.mean(img_cv, axis=(0, 1))  # [B, G, R] in OpenCV
    b_avg, g_avg, r_avg = avg_color

    # Simple color temperature estimation
    # Warmer images (more red) = lower color temp (2000-4000K)
    # Cooler images (more blue) = higher color temp (6000-10000K)
    if r_avg > 0:
        ratio = b_avg / r_avg
        # Map ratio to color temperature range
        if ratio < 0.8:
            analysis["color_temp"] = 2500  # Very warm (sunset, tungsten)
        elif ratio < 0.95:
            analysis["color_temp"] = 3500  # Warm (indoor)
        elif ratio < 1.05:
            analysis["color_temp"] = 5000  # Neutral (daylight)
        elif ratio < 1.2:
            analysis["color_temp"] = 6500  # Cool (overcast)
        else:
            analysis["color_temp"] = 8000  # Very cool (shade)

    # Detect potential flash usage
    # Flash typically creates bright center with darker edges
    center_region = gray[height // 3 : 2 * height // 3, width // 3 : 2 * width // 3]
    edge_brightness = np.mean(
        [
            np.mean(gray[0 : height // 4, :]),
            np.mean(gray[3 * height // 4 :, :]),
            np.mean(gray[:, 0 : width // 4]),
            np.mean(gray[:, 3 * width // 4 :]),
        ]
    )
    center_brightness = np.mean(center_region)

    if center_brightness > edge_brightness * 1.5 and avg_brightness > 150:
        analysis["has_flash"] = True

    print(
        f"  Image analysis: {width}x{height}, orientation={analysis['orientation']}, "
        f"brightness={analysis['brightness']:.2f}, color_temp={analysis['color_temp']}K, "
        f"flash={'Yes' if analysis['has_flash'] else 'No'}"
    )

    return analysis


def estimate_camera_settings(image_analysis):
    """
    Estimate realistic camera settings based on image analysis.
    Returns a dictionary with camera settings.

    Args:
        image_analysis: Dictionary with analyzed image properties
    """
    brightness = image_analysis["brightness"]
    has_flash = image_analysis["has_flash"]

    settings = {}

    # Estimate ISO based on brightness
    # Darker scenes need higher ISO
    if has_flash:
        # Flash photos typically use lower ISO
        iso_options = [100, 125, 160, 200, 250, 320, 400]
        settings["iso"] = random.choice(iso_options)
    elif brightness < -3:  # Very dark
        iso_options = [1600, 2000, 2500, 3200]
        settings["iso"] = random.choice(iso_options)
    elif brightness < 0:  # Dark
        iso_options = [640, 800, 1000, 1250, 1600]
        settings["iso"] = random.choice(iso_options)
    elif brightness < 3:  # Normal
        iso_options = [200, 250, 320, 400, 500, 640]
        settings["iso"] = random.choice(iso_options)
    else:  # Bright
        iso_options = [32, 50, 64, 80, 100, 125, 160]
        settings["iso"] = random.choice(iso_options)

    # Estimate shutter speed based on brightness and ISO
    # Darker = slower shutter, but iPhone has stabilization
    if has_flash:
        # Flash sync speed range
        shutter_options = [(1, 60), (1, 80), (1, 100), (1, 125)]
    elif brightness < -3:  # Very dark
        shutter_options = [(1, 4), (1, 8), (1, 10), (1, 15)]
    elif brightness < 0:  # Dark
        shutter_options = [(1, 15), (1, 20), (1, 30), (1, 40), (1, 60)]
    elif brightness < 3:  # Normal
        shutter_options = [(1, 60), (1, 80), (1, 100), (1, 125), (1, 160), (1, 200)]
    else:  # Bright
        shutter_options = [
            (1, 250),
            (1, 320),
            (1, 400),
            (1, 500),
            (1, 640),
            (1, 800),
            (1, 1000),
        ]

    settings["shutter_speed"] = random.choice(shutter_options)

    # iPhone 15 has two main lenses
    # Wide: f/1.6, 5.96mm (26mm equivalent)
    # Ultra-wide: f/2.4, 2.22mm (13mm equivalent)
    # Choose based on image aspect and randomness
    if random.random() < 0.8:  # 80% use wide lens (most common)
        settings["aperture"] = (16, 10)  # f/1.6
        settings["focal_length"] = (596, 100)  # 5.96mm
        settings["focal_length_35mm"] = 26
        settings["lens_model"] = b"iPhone 15 back dual wide camera 5.96mm f/1.6"
        settings["lens_spec"] = (
            (154, 100),  # Min focal length: 1.54mm
            (596, 100),  # Max focal length: 5.96mm
            (16, 10),  # Min f-number: f/1.6
            (24, 10),  # Max f-number: f/2.4
        )
    else:  # 20% use ultra-wide
        settings["aperture"] = (24, 10)  # f/2.4
        settings["focal_length"] = (222, 100)  # 2.22mm
        settings["focal_length_35mm"] = 13
        settings["lens_model"] = b"iPhone 15 back dual wide camera 2.22mm f/2.4"
        settings["lens_spec"] = (
            (154, 100),  # Min focal length: 1.54mm
            (596, 100),  # Max focal length: 5.96mm
            (16, 10),  # Min f-number: f/1.6
            (24, 10),  # Max f-number: f/2.4
        )

    # Exposure compensation (usually small adjustments)
    # Bias toward 0, but allow ±1 EV range
    ev_options = [
        (0, 1),  # 0 EV (most common)
        (0, 1),
        (0, 1),
        (0, 1),  # Weight toward 0
        (-333, 1000),
        (-667, 1000),  # -0.33, -0.67 EV
        (333, 1000),
        (667, 1000),  # +0.33, +0.67 EV
        (-1000, 1000),
        (1000, 1000),  # ±1 EV
    ]
    settings["exposure_compensation"] = random.choice(ev_options)

    # Metering mode - vary based on scene
    # Multi-pattern is most common on iPhone
    metering_options = [
        5,  # Multi-spot/Pattern (most common)
        5,
        5,
        5,  # Weight toward multi-pattern
        2,  # Center-weighted average
        3,  # Spot
    ]
    settings["metering_mode"] = random.choice(metering_options)

    # Subsecond time (milliseconds)
    settings["subsec_time"] = str(random.randint(0, 999)).zfill(3).encode()

    print(
        f"  Camera settings: ISO {settings['iso']}, {settings['shutter_speed'][0]}/{settings['shutter_speed'][1]}s, "
        f"f/{settings['aperture'][0]/settings['aperture'][1]:.1f}, {settings['focal_length_35mm']}mm"
    )

    return settings


def detect_subject_area(img):
    """
    Detect the main subject in the image using face detection or saliency.
    Returns (center_x, center_y, width, height) or None if no subject detected.

    Args:
        img: PIL Image object
    """
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    height, width = img_cv.shape[:2]

    # Try face detection first
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    if len(faces) > 0:
        # Use the largest face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face
        center_x = x + w // 2
        center_y = y + h // 2
        print(f"  Detected face at center ({center_x}, {center_y}) with size {w}x{h}")
        return (center_x, center_y, w, h)

    # If no face, try saliency detection
    try:
        saliency = cv2.saliency.StaticSaliencyFineGrained_create()
        success, saliency_map = saliency.computeSaliency(img_cv)

        if success:
            # Threshold the saliency map
            _, thresh_map = cv2.threshold(
                (saliency_map * 255).astype(np.uint8), 127, 255, cv2.THRESH_BINARY
            )

            # Find contours
            contours, _ = cv2.findContours(
                thresh_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                # Get the largest contour
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2
                print(
                    f"  Detected salient region at center ({center_x}, {center_y}) with size {w}x{h}"
                )
                return (center_x, center_y, w, h)
    except Exception as e:
        print(f"  Saliency detection failed: {e}")

    # Fallback: use center of image with reasonable size
    center_x = width // 2
    center_y = height // 2
    area_w = width // 3
    area_h = height // 3
    print(
        f"  No subject detected, using image center ({center_x}, {center_y}) with size {area_w}x{area_h}"
    )
    return (center_x, center_y, area_w, area_h)


def create_exif_data(subject_area=None, image_analysis=None):
    """
    Create EXIF data dictionary based on the sample.txt reference.
    Returns a piexif-compatible EXIF dictionary.

    Args:
        subject_area: Tuple of (center_x, center_y, width, height) for the main subject
        image_analysis: Dictionary with analyzed image properties
    """

    now = datetime.now()
    random_days = random.uniform(0, 3)
    random_dt = now - timedelta(days=random_days)
    datetime_str = random_dt.strftime("%Y:%m:%d %H:%M:%S").encode()

    # Use provided subject area or default
    if subject_area is None:
        subject_area = (1887, 1945, 748, 753)

    # Use analyzed values or defaults
    if image_analysis is None:
        image_analysis = {
            "width": 4032,
            "height": 3024,
            "orientation": 6,
            "brightness": -5.006109058,
            "color_temp": 4921,
            "has_flash": False,
        }

    # Calculate brightness value for EXIF (as rational)
    # Use smaller denominator to keep within 32-bit signed integer limits
    brightness_rational = (int(image_analysis["brightness"] * 1000000), 1000000)

    # Estimate realistic camera settings
    camera_settings = estimate_camera_settings(image_analysis)

    # EXIF IFD (Image File Directory)
    exif_ifd = {
        piexif.ExifIFD.ExposureTime: camera_settings["shutter_speed"],
        piexif.ExifIFD.FNumber: camera_settings["aperture"],
        piexif.ExifIFD.ExposureProgram: 2,  # Program AE
        piexif.ExifIFD.ISOSpeedRatings: camera_settings["iso"],
        piexif.ExifIFD.ExifVersion: b"0232",
        piexif.ExifIFD.DateTimeOriginal: datetime_str,
        piexif.ExifIFD.DateTimeDigitized: datetime_str,
        piexif.ExifIFD.ShutterSpeedValue: camera_settings["shutter_speed"],
        piexif.ExifIFD.ApertureValue: camera_settings["aperture"],
        piexif.ExifIFD.BrightnessValue: brightness_rational,
        piexif.ExifIFD.ExposureBiasValue: camera_settings["exposure_compensation"],
        piexif.ExifIFD.MeteringMode: camera_settings["metering_mode"],
        piexif.ExifIFD.Flash: (
            1 if image_analysis["has_flash"] else 16
        ),  # Flash fired or not
        piexif.ExifIFD.FocalLength: camera_settings["focal_length"],
        piexif.ExifIFD.SubjectArea: subject_area,
        piexif.ExifIFD.SubSecTimeOriginal: camera_settings["subsec_time"],
        piexif.ExifIFD.SubSecTimeDigitized: camera_settings["subsec_time"],
        piexif.ExifIFD.ColorSpace: 65535,  # Uncalibrated
        piexif.ExifIFD.PixelXDimension: image_analysis["width"],
        piexif.ExifIFD.PixelYDimension: image_analysis["height"],
        piexif.ExifIFD.SensingMethod: 2,  # One-chip color area
        piexif.ExifIFD.SceneType: b"\x01",  # Directly photographed
        piexif.ExifIFD.ExposureMode: 0,  # Auto
        piexif.ExifIFD.WhiteBalance: 0,  # Auto
        piexif.ExifIFD.FocalLengthIn35mmFilm: camera_settings["focal_length_35mm"],
        piexif.ExifIFD.LensSpecification: camera_settings["lens_spec"],
        piexif.ExifIFD.LensMake: b"Apple",
        piexif.ExifIFD.LensModel: camera_settings["lens_model"],
    }

    # 0th IFD (Main Image)
    zeroth_ifd = {
        piexif.ImageIFD.Make: b"Apple",
        piexif.ImageIFD.Model: b"iPhone 15",
        piexif.ImageIFD.Orientation: image_analysis["orientation"],
        piexif.ImageIFD.XResolution: (72, 1),
        piexif.ImageIFD.YResolution: (72, 1),
        piexif.ImageIFD.ResolutionUnit: 2,  # inches
        piexif.ImageIFD.Software: b"26.0",
        piexif.ImageIFD.DateTime: datetime_str,
        piexif.ImageIFD.HostComputer: b"iPhone 15",
    }

    # Combine all IFDs
    exif_dict = {
        "0th": zeroth_ifd,
        "Exif": exif_ifd,
    }

    return exif_dict


def generate_iphone_filename(directory):
    """
    Generate an iPhone-style filename (IMG_XXXX.JPG) that doesn't exist in the directory.
    
    Args:
        directory: Directory where the file will be saved
    """
    # Find existing IMG_XXXX.JPG files to avoid conflicts
    existing_numbers = set()
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.startswith('IMG_') and filename.endswith('.JPG'):
                try:
                    num = int(filename[4:8])
                    existing_numbers.add(num)
                except ValueError:
                    continue
    
    # Generate a random 4-digit number that doesn't exist
    while True:
        img_number = random.randint(1000, 9999)
        if img_number not in existing_numbers:
            return f"IMG_{img_number}.JPG"


def modify_image_exif(input_path, output_path=None):
    """
    Modify the EXIF metadata of an image.

    Args:
        input_path: Path to the input image
        output_path: Path to save the modified image (if None, generates iPhone-style name)
    """

    if not os.path.exists(input_path):
        print(f"Error: File '{input_path}' not found.")
        return False

    # Open the image
    img = Image.open(input_path)

    # Analyze image properties
    print("Analyzing image properties...")
    image_analysis = analyze_image(img)

    # Detect subject area
    print("Detecting subject in image...")
    subject_area = detect_subject_area(img)

    # Create EXIF data with detected subject area and analysis
    exif_dict = create_exif_data(
        subject_area=subject_area, image_analysis=image_analysis
    )
    exif_bytes = piexif.dump(exif_dict)

    # Determine output path - generate iPhone-style filename
    if output_path is None:
        input_dir = os.path.dirname(os.path.abspath(input_path))
        output_filename = generate_iphone_filename(input_dir)
        output_path = os.path.join(input_dir, output_filename)

    # Save image with new EXIF data
    # Convert to RGB if necessary (for PNG or other formats)
    if img.mode in ("RGBA", "LA", "P"):
        # Create a white background
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if "A" in img.mode:
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
        else:
            background.paste(img)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Save with EXIF data as JPEG
    img.save(output_path, "JPEG", exif=exif_bytes, quality=95)

    print(f"✓ Successfully processed: {input_path}")
    print(f"  Saved to: {output_path}")

    return True


def modify_image_exif_folder(input_folder, output_folder):
    if not output_folder:
        output_folder = input_folder

    for filename in os.listdir(input_folder):
        _, file_extension = os.path.splitext(filename)
        if file_extension.lower() in (".jpg", ".jpeg", ".png"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            modify_image_exif(input_path, output_path)


if __name__ == "__main__":
    input_path = "/Users/ashegaonkar/Downloads"

    if os.path.isdir(input_path):
        print(f"Modifying images in folder: {input_path}")
        output_path = os.path.join(input_path, "exif_output")
        os.makedirs(output_path, exist_ok=True)
        modify_image_exif_folder(input_path, output_path)
    else:
        print(f"Modifying image: {input_path}")
        modify_image_exif(input_path)
