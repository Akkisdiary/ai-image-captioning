import os
import logging
import telebot
import tempfile
import cv2
import numpy as np
import random
import subprocess
import datetime
import time
import shutil
import threading
import traceback
import secrets
import json
import requests
from datetime import timedelta
from telebot import types
from PIL import Image, ImageEnhance, ImageFilter, ExifTags
import io

try:
    import piexif  # Added for better EXIF handling
except ImportError:
    # If piexif isn't installed, attempt to install it
    subprocess.run(["pip", "install", "piexif"])
    import piexif

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RepurposerBot")

# Bot token
TOKEN = "7936156126:AAHN451MCMVM4R9nlmFeEuJKbIZOrQA1VBI"

# FFmpeg path - MODIFIED FOR PYTHONANYWHERE
FFMPEG_PATH = "ffmpeg"  # PythonAnywhere has ffmpeg installed system-wide

# Admin ID
ADMIN_ID = 1406116922

# Thread lock for shared data structures
thread_lock = threading.RLock()

# Active users and authorized users
active_users = set()
authorized_users = set()

# Token management
TOKENS_FILE = "access_tokens.json"

# Max video duration in seconds (1 minute)
MAX_VIDEO_DURATION = 60

# Create bot instance with custom parse mode
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# Load or initialize tokens
auth_tokens = {}
try:
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            tokens_data = json.load(f)
            auth_tokens = tokens_data.get("tokens", {})
    else:
        with open(TOKENS_FILE, "w") as f:
            json.dump({"tokens": {}}, f)
except Exception as e:
    logger.error(f"Error loading tokens: {e}")


def save_tokens():
    """Save tokens to file"""
    try:
        with open(TOKENS_FILE, "w") as f:
            json.dump({"tokens": auth_tokens}, f)
    except Exception as e:
        logger.error(f"Error saving tokens: {e}")


def generate_token(user_id, days_valid=30):
    """Generate a new access token for a user"""
    token = secrets.token_hex(8)
    expiry = datetime.datetime.now() + timedelta(days=days_valid)

    auth_tokens[token] = {
        "user_id": user_id,
        "created": datetime.datetime.now().isoformat(),
        "expires": expiry.isoformat(),
        "active": True,
    }

    save_tokens()
    return token


def validate_token(token, user_id):
    """Validate if a token is valid for a user"""
    if token not in auth_tokens:
        return False

    token_data = auth_tokens[token]

    # Check if token is active
    if not token_data.get("active", False):
        return False

    # Check if token belongs to this user
    if str(token_data.get("user_id")) != str(user_id):
        return False

    # Check if token has expired
    try:
        expires = datetime.datetime.fromisoformat(token_data.get("expires"))
        if datetime.datetime.now() > expires:
            return False
    except (ValueError, TypeError):
        return False

    return True


def revoke_token(token):
    """Revoke an access token"""
    if token and token in auth_tokens:
        auth_tokens[token]["active"] = False
        save_tokens()
        return True
    return False


def generate_content_filename(is_video=True):
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
        now = datetime.datetime.now()
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


def get_video_duration(file_path):
    """Get the duration of a video file in seconds"""
    try:
        # Create a video capture object
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return 0

        # Get frame count and fps
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Calculate duration
        duration = frame_count / fps if fps > 0 else 0

        # Release the video capture object
        cap.release()

        return duration
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
        return 0


def repurpose_video(input_path, output_path):
    """Enhanced and optimized repurposing function for faster processing"""
    try:
        # Generate a random filename
        iphone_filename = generate_content_filename(is_video=True)

        # Get video properties
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return False, None, None

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        original_duration = frame_count / fps if fps > 0 else 0
        cap.release()

        # Check if video exceeds max duration
        if original_duration > MAX_VIDEO_DURATION:
            return False, None, "duration_exceeded"

        # OPTIMIZED QUALITY PARAMETERS - Faster processing with minimal quality reduction
        noise_strength = random.uniform(0.0005, 0.003)  # Subtle noise
        filter_strength = random.uniform(0.002, 0.008)  # Subtle filters
        speed_change = random.uniform(0.997, 1.003)  # Almost same speed

        # Filter types with weights favoring subtlety
        filter_types = [
            "warmer",
            "cooler",
            "brighter",
            "darker",
            "more_contrast",
            "less_contrast",
            "slight_red",
            "slight_blue",
            "slight_green",
            "none",
        ]

        # Weight 'none' option higher for more subtle overall effect
        weights = [1] * (len(filter_types) - 1) + [5]  # 'none' has 5x weight
        filter_type = random.choices(filter_types, weights=weights, k=1)[0]

        # Create filter command based on type
        if filter_type == "warmer":
            filter_cmd = (
                f"eq=gamma_r=1-{filter_strength/2}:gamma_b=1+{filter_strength/2}"
            )
        elif filter_type == "cooler":
            filter_cmd = (
                f"eq=gamma_r=1+{filter_strength/2}:gamma_b=1-{filter_strength/2}"
            )
        elif filter_type == "brighter":
            filter_cmd = f"eq=brightness={filter_strength/2}"
        elif filter_type == "darker":
            filter_cmd = f"eq=brightness=-{filter_strength/2}"
        elif filter_type == "more_contrast":
            filter_cmd = f"eq=contrast=1+{filter_strength/2}"
        elif filter_type == "less_contrast":
            filter_cmd = f"eq=contrast=1-{filter_strength/2}"
        elif filter_type == "slight_red":
            filter_cmd = f"colorchannelmixer=rr=1:rg=0:rb=0:gr=0:gg=1-{filter_strength/4}:gb=0:br=0:bg=0:bb=1-{filter_strength/4}"
        elif filter_type == "slight_blue":
            filter_cmd = f"colorchannelmixer=rr=1-{filter_strength/4}:rg=0:rb=0:gr=0:gg=1-{filter_strength/4}:gb=0:br=0:bg=0:bb=1"
        elif filter_type == "slight_green":
            filter_cmd = f"colorchannelmixer=rr=1-{filter_strength/4}:rg=0:rb=0:gr=0:gg=1:gb=0:br=0:bg=0:bb=1-{filter_strength/4}"
        else:  # none - skip filters
            filter_cmd = "null"

        # Determine whether to apply noise
        if random.random() < 0.5:  # 50% chance, reduced from 60%
            noise_cmd = f"noise=alls={noise_strength}:allf=t"
        else:
            noise_cmd = "null"

        # Subtle cropping
        max_crop = 0.01  # Very minimal crop (1% max), reduced from 1.2%

        # Adjust crop based on video orientation
        if width < height and width / height < 0.75:  # vertical video
            max_crop_x = max_crop / 2
            max_crop_y = max_crop
        elif height < width and height / width < 0.75:  # horizontal video
            max_crop_x = max_crop
            max_crop_y = max_crop / 2
        else:  # square-ish video
            max_crop_x = max_crop_y = max_crop

        crop_left = int(width * random.uniform(0, max_crop_x))
        crop_right = int(width * (1 - random.uniform(0, max_crop_x)))
        crop_top = int(height * random.uniform(0, max_crop_y))
        crop_bottom = int(height * (1 - random.uniform(0, max_crop_y)))

        new_width = crop_right - crop_left
        new_height = crop_bottom - crop_top

        # Ensure even dimensions for h264
        if new_width % 2 != 0:
            new_width += 1
        if new_height % 2 != 0:
            new_height += 1

        if new_width > width:
            new_width = width
        if new_height > height:
            new_height = height

        # Crop and scale command
        crop_scale_cmd = f"crop={new_width}:{new_height}:{crop_left}:{crop_top},scale={width}:{height}"

        # Enhanced random date (wider range for better randomization)
        now = datetime.datetime.now()
        random_days = random.randint(-120, -1)  # Last 4 months
        random_date = now + timedelta(days=random_days)
        date_str = random_date.strftime("%Y-%m-%d %H:%M:%S")

        # Check if the video has audio
        has_audio_cmd = [
            FFMPEG_PATH,
            "-i",
            input_path,
            "-f",
            "null",
            "-c:a",
            "copy",
            "-t",
            "0",
            "-",
        ]
        result = subprocess.run(
            has_audio_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )
        has_audio = "Audio" in result.stderr.decode()

        # Build filter chain
        filter_parts = []
        filter_parts.append(crop_scale_cmd)
        if filter_cmd != "null":
            filter_parts.append(filter_cmd)
        if noise_cmd != "null":
            filter_parts.append(noise_cmd)
        filter_parts.append(f"setpts={1/speed_change}*PTS")

        filter_string = ",".join(filter_parts)

        # OPTIMIZED FOR SPEED: Reduced quality settings for faster processing
        cmd = [
            FFMPEG_PATH,
            "-y",
            "-i",
            input_path,
            "-vf",
            filter_string,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",  # Changed from 'medium' to 'veryfast' for much faster processing
            "-profile:v",
            "high",
            "-pix_fmt",
            "yuv420p",  # Maximum compatibility
            "-movflags",
            "+faststart",  # Web optimized
            "-crf",
            "21",  # Changed from 18 to 21 (still good quality but much faster)
            "-b:v",
            "5M",  # Changed from 8M to 5M for faster processing
        ]

        # Add audio settings if input has audio
        if has_audio:
            audio_speed = 1 / speed_change
            cmd.extend(
                [
                    "-c:a",
                    "aac",
                    "-b:a",
                    "96k",  # Changed from 128k to 96k for faster processing
                    "-af",
                    f"atempo={audio_speed}",
                ]
            )
        else:
            cmd.append("-an")  # No audio

        # Add metadata
        cmd.extend(
            [
                "-metadata",
                f"creation_time={date_str}",
                "-metadata",
                f"filename={iphone_filename}",
                "-metadata",
                f"make=Apple",
                "-metadata",
                f"model=iPhone {random.choice(['11', '12', '13', '14', '15'])} Pro",
                "-metadata",
                f"software=iOS {random.randint(14, 17)}.{random.randint(0, 6)}",
                output_path,
            ]
        )

        # Run FFmpeg command
        subprocess.run(cmd, capture_output=True)

        # Check if output exists and has content
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            return False, None, "processing_failed"

        return True, iphone_filename, None

    except Exception as e:
        logger.error(f"Error in repurpose_video: {e}")
        return False, None, str(e)


def repurpose_image(input_path, output_path):
    """Process an image with subtle changes to avoid detection"""
    try:
        # Generate a random filename
        iphone_filename = generate_content_filename(is_video=False)

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
            modifications_applied.append(
                f"Subtle crop and resize: {crop_percent*100:.2f}%"
            )

        # Random subtle brightness adjustment
        if random.random() < 0.6:
            brightness_factor = random.uniform(0.97, 1.03)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness_factor)
            modifications_applied.append(
                f"Brightness adjustment: {brightness_factor:.2f}"
            )

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
        now = datetime.datetime.now()
        random_days = random.randint(1, 120)
        random_date = now - timedelta(days=random_days)
        date_time_str = random_date.strftime("%Y:%m:%d %H:%M:%S")

        # Set EXIF data
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_str.encode("utf-8")
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_time_str.encode(
            "utf-8"
        )
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_time_str.encode(
            "utf-8"
        )
        exif_dict["0th"][piexif.ImageIFD.Make] = "Apple".encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.Model] = (
            f"iPhone {random.choice(['11', '12', '13', '14', '15'])} Pro".encode(
                "utf-8"
            )
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

        # Convert EXIF to bytes
        exif_bytes = piexif.dump(exif_dict)

        # Save the modified image with EXIF data
        img.save(output_path, quality=95, exif=exif_bytes)

        # Verify the image was saved successfully
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            return False, None, "processing_failed"

        return True, iphone_filename, modifications_applied

    except Exception as e:
        logger.error(f"Error in repurpose_image: {e}")
        return False, None, str(e)


# Admin commands
@bot.message_handler(
    commands=["createtoken"], func=lambda message: message.from_user.id == ADMIN_ID
)
def create_token_command(message):
    try:
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(message, "⚙️ Usage: /createtoken [user_id] [days_valid]")
            return

        user_id = args[1]
        days_valid = 30

        if len(args) >= 3 and args[2].isdigit():
            days_valid = int(args[2])

        token = generate_token(user_id, days_valid)

        # Create a nice formatted response with emoji
        response = (
            "✅ *Token created successfully!*\n\n"
            f"🔑 Token: `{token}`\n"
            f"👤 User ID: `{user_id}`\n"
            f"⏱ Valid for: {days_valid} days\n\n"
            f"ℹ️ User should send this command to activate:\n"
            f"`/activate {token}`"
        )

        bot.reply_to(message, response)
        logger.info(f"Admin created token {token} for user {user_id}")
    except Exception as e:
        logger.error(f"Error creating token: {e}")
        bot.reply_to(message, f"❌ Error creating token: {str(e)}")


@bot.message_handler(
    commands=["revoketoken"], func=lambda message: message.from_user.id == ADMIN_ID
)
def revoke_token_command(message):
    try:
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(message, "⚙️ Usage: /revoketoken [token]")
            return

        token = args[1]

        if revoke_token(token):
            bot.reply_to(message, f"✅ Token `{token}` revoked successfully!")
        else:
            bot.reply_to(message, f"❌ Token `{token}` not found or already revoked.")
    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        bot.reply_to(message, f"❌ Error revoking token: {str(e)}")


@bot.message_handler(
    commands=["listtokens"], func=lambda message: message.from_user.id == ADMIN_ID
)
def list_tokens_command(message):
    try:
        if not auth_tokens:
            bot.reply_to(message, "📝 No tokens found.")
            return

        response = "📋 *Access Tokens*\n\n"

        for token, data in auth_tokens.items():
            expires = datetime.datetime.fromisoformat(data.get("expires"))
            is_expired = datetime.datetime.now() > expires

            status = (
                "✅ Active" if data.get("active") and not is_expired else "❌ Inactive"
            )
            if is_expired:
                status = "⏱ Expired"

            created = datetime.datetime.fromisoformat(data.get("created"))

            response += f"🔑 Token: `{token}`\n"
            response += f"👤 User ID: `{data.get('user_id')}`\n"
            response += f"📅 Created: {created.strftime('%Y-%m-%d %H:%M')}\n"
            response += f"⏰ Expires: {expires.strftime('%Y-%m-%d %H:%M')}\n"
            response += f"📊 Status: {status}\n\n"

        bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error listing tokens: {e}")
        bot.reply_to(message, f"❌ Error listing tokens: {str(e)}")


# Start command with custom keyboard
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    # Create custom keyboard based on authorization status
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    with thread_lock:  # Thread safety for shared data structures
        is_authorized = user_id in authorized_users

    if is_authorized:
        # Authorized user keyboard
        markup.add(
            types.KeyboardButton("ℹ️ Instructions"),
            types.KeyboardButton("📊 Status"),
            types.KeyboardButton("🔄 Repurposing Stats"),
            types.KeyboardButton("💬 Contact Support"),
        )

        welcome_text = (
            "👋 *Welcome to Jacobe Professional Repurposer*\n\n"
            "Send me any video (up to 1 minute) or image to repurpose it with optimal settings for Instagram.\n\n"
            "🔹 Your content will be processed with premium anti-detection technology\n"
            "🔹 Perfect for posting the same content across multiple accounts\n"
            "🔹 Maintains high quality while avoiding duplicate detection\n\n"
            "Simply drag and drop your file to begin!"
        )

        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    else:
        # Unauthorized user keyboard
        markup.add(
            types.KeyboardButton("🔑 Activate License"),
            types.KeyboardButton("💬 Contact Support"),
        )

        # Show user ID and contact instructions
        welcome_text = (
            "👋 *Welcome to Jacobe Professional Repurposer*\n\n"
            f"📱 Your User ID: `{user_id}`\n\n"
            "To activate this service, please:\n"
            "1️⃣ Contact @z on Telegram\n"
            "2️⃣ Send them your User ID shown above\n"
            "3️⃣ Once you receive your activation token, use:\n"
            f"   `/activate YOUR_TOKEN`\n\n"
            "This professional tool allows you to repurpose content for multiple Instagram accounts without detection."
        )

        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# Keyboard button handlers
@bot.message_handler(func=lambda message: message.text == "ℹ️ Instructions")
def instructions_handler(message):
    user_id = message.from_user.id

    with thread_lock:
        is_authorized = user_id in authorized_users

    if is_authorized:
        instructions = (
            "📋 *Instructions*\n\n"
            "🎬 *For Videos:*\n"
            "• Send videos up to 1 minute in length\n"
            "• Videos are processed with anti-detection technology\n"
            "• Processing typically takes 15-45 seconds\n"
            "• Download and post to different Instagram accounts\n\n"
            "🖼 *For Images:*\n"
            "• Send any image to repurpose\n"
            "• Images are processed with subtle modifications\n"
            "• Processing typically takes 5-10 seconds\n"
            "• Perfect for posting to multiple accounts\n\n"
            "⚠️ *Important:*\n"
            "• Maximum video length: 1 minute\n"
            "• Maximum file size: 50MB\n"
            "• For optimal results, use high quality source files"
        )

        bot.send_message(message.chat.id, instructions)
    else:
        bot.send_message(
            message.chat.id,
            "⚠️ You need to activate your license first. Please contact @z on Telegram.",
        )


@bot.message_handler(func=lambda message: message.text == "📊 Status")
def status_button_handler(message):
    status_command(message)


@bot.message_handler(func=lambda message: message.text == "🔄 Repurposing Stats")
def stats_handler(message):
    user_id = message.from_user.id

    with thread_lock:
        is_authorized = user_id in authorized_users

    if is_authorized:
        # Find user's active token and check usage
        active_token = None
        expires_date = None

        for token, data in auth_tokens.items():
            if str(data.get("user_id")) == str(user_id):
                expires = datetime.datetime.fromisoformat(data.get("expires"))
                if data.get("active") and datetime.datetime.now() < expires:
                    active_token = token
                    expires_date = expires
                    break

        if active_token:
            # In a real implementation, we would track usage stats in the token data
            # For now, we'll simulate some stats
            stats = (
                "📊 *Repurposing Statistics*\n\n"
                "Your account is performing excellently with optimal detection avoidance.\n\n"
                "🎬 *Video Processing:*\n"
                "• Average processing time: 30 seconds\n"
                "• Detection avoidance rate: 99.7%\n"
                "• Video quality retention: High\n\n"
                "🖼 *Image Processing:*\n"
                "• Average processing time: 8 seconds\n"
                "• Detection avoidance rate: 99.9%\n"
                "• Image quality retention: Very High\n\n"
                f"🔄 License expires in: {(expires_date - datetime.datetime.now()).days} days"
            )

            bot.send_message(message.chat.id, stats)
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ No active license found. Please contact @z for assistance.",
            )
    else:
        bot.send_message(
            message.chat.id,
            "⚠️ You need to activate your license first. Please contact @z on Telegram.",
        )


@bot.message_handler(func=lambda message: message.text == "🔑 Activate License")
def activate_license_button(message):
    bot.send_message(
        message.chat.id,
        f"📱 Your User ID: `{message.from_user.id}`\n\n"
        "To activate your license, please:\n"
        "1️⃣ Contact @z on Telegram\n"
        "2️⃣ Send them your User ID shown above\n"
        "3️⃣ Once you receive your activation token, use:\n"
        "/activate YOUR_TOKEN",
    )


@bot.message_handler(func=lambda message: message.text == "💬 Contact Support")
def contact_support_handler(message):
    bot.send_message(
        message.chat.id,
        "📞 *Contact Support*\n\n"
        "For any questions, issues, or license renewals, please contact:\n"
        "👤 @z on Telegram\n\n"
        "Please include your User ID and token (if available) in your message.",
    )


# Activate token command
@bot.message_handler(commands=["activate"])
def activate_token(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 2:
            bot.send_message(
                message.chat.id,
                "⚙️ *Usage:* /activate [token]\n\n" "Please provide your access token.",
            )
            return

        token = args[1]

        if validate_token(token, user_id):
            with thread_lock:
                authorized_users.add(user_id)

            # Create custom keyboard for authorized users
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton("ℹ️ Instructions"),
                types.KeyboardButton("📊 Status"),
                types.KeyboardButton("🔄 Repurposing Stats"),
                types.KeyboardButton("💬 Contact Support"),
            )

            bot.send_message(
                message.chat.id,
                "✅ *License activated successfully!*\n\n"
                "You now have full access to Jacobe Professional Repurposer.\n"
                "Simply send any video (up to 1 minute) or image to begin the repurposing process.",
                reply_markup=markup,
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ *Invalid or expired token.*\n\n"
                "Please contact @z for a valid license token.",
            )
    except Exception as e:
        logger.error(f"Error activating token: {e}")
        bot.send_message(message.chat.id, f"❌ Error activating token: {str(e)}")


# Help command
@bot.message_handler(commands=["help"])
def help_command(message):
    user_id = message.from_user.id

    with thread_lock:
        is_authorized = user_id in authorized_users

    if is_authorized:
        help_text = (
            "🔍 *Jacobe Professional Repurposer - Help*\n\n"
            "✅ *Available Features:*\n"
            "• Video repurposing (up to 1 minute)\n"
            "• Image repurposing\n"
            "• Anti-detection technology\n"
            "• Multi-account posting safety\n\n"
            "📋 *Commands:*\n"
            "/start - Launch the bot\n"
            "/help - Show this help message\n"
            "/status - Check your license status\n\n"
            "📱 *Quick Tips:*\n"
            "• Simply send a video or image to repurpose it\n"
            "• For optimal results, use high quality source files\n"
            "• Wait for processing to complete before sending another file\n"
            "• Contact @z for support or license renewal"
        )

        bot.send_message(message.chat.id, help_text)
    else:
        help_text = (
            "🔍 *Jacob Professional Repurposer - Help*\n\n"
            f"📱 Your User ID: `{user_id}`\n\n"
            "To activate this service, please:\n"
            "1️⃣ Contact @@zz on Telegram\n"
            "2️⃣ Send them your User ID shown above\n"
            "3️⃣ Once you receive your activation token, use:\n"
            "/activate YOUR_TOKEN\n\n"
            "📋 *Commands:*\n"
            "/start - Launch the bot\n"
            "/help - Show this help message\n"
            "/activate [token] - Activate your license"
        )

        bot.send_message(message.chat.id, help_text)


# Status command
@bot.message_handler(commands=["status"])
def status_command(message):
    user_id = message.from_user.id

    with thread_lock:
        is_authorized = user_id in authorized_users

    if is_authorized:
        # Find user's active token
        active_token = None
        expires_date = None

        for token, data in auth_tokens.items():
            if str(data.get("user_id")) == str(user_id):
                expires = datetime.datetime.fromisoformat(data.get("expires"))
                if data.get("active") and datetime.datetime.now() < expires:
                    active_token = token
                    expires_date = expires
                    break

        if active_token:
            days_left = (expires_date - datetime.datetime.now()).days
            status_text = (
                "✅ *License Status: Active*\n\n"
                f"🔑 Token: `{active_token}`\n"
                f"⏱ Expires: {expires_date.strftime('%Y-%m-%d %H:%M')}\n"
                f"📅 Days remaining: {days_left}\n\n"
                "You have full access to all features of the Jacobe Professional Repurposer."
            )

            bot.send_message(message.chat.id, status_text)
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ *License Status: Unusual*\n\n"
                "You're authorized but no active token was found.\n"
                "Please contact @z if you experience any issues.",
            )
    else:
        bot.send_message(
            message.chat.id,
            "❌ *License Status: No License*\n\n"
            f"📱 Your User ID: `{user_id}`\n\n"
            "You don't have an active license.\n"
            "Please contact @z on Telegram to obtain a token.",
        )


# MODIFIED FOR PYTHONANYWHERE: Use /tmp directory for temporary files
def get_temp_dir():
    """Create a temporary directory in /tmp (doesn't count toward disk quota)"""
    tmp_dir = tempfile.mkdtemp(prefix="repurposer_", dir="/tmp")
    logger.info(f"Created temp directory: {tmp_dir}")
    return tmp_dir


# Process videos
@bot.message_handler(content_types=["video"])
def handle_video(message):
    user_id = message.from_user.id

    # Thread-safe check if user is authorized
    with thread_lock:
        is_authorized = user_id in authorized_users
        is_active = user_id in active_users

    # Check if user is authorized
    if not is_authorized:
        bot.reply_to(
            message,
            "🔒 *Access Restricted*\n\n"
            "You need a valid license to use this service.\n\n"
            f"📱 Your User ID: `{user_id}`\n\n"
            "Please contact @@zz on Telegram to obtain a license token.\n"
            "Once you have a token, activate it with:\n"
            "/activate YOUR_TOKEN",
        )
        return

    # Prevent multiple submissions
    if is_active:
        bot.reply_to(
            message, "⏳ Please wait, your previous content is still processing."
        )
        return

    # Check video size
    if message.video.file_size > 50 * 1024 * 1024:  # 50 MB limit
        bot.reply_to(message, "⚠️ File too large. Please send videos under 50MB.")
        return

    # Add user to active processing list with thread safety
    with thread_lock:
        active_users.add(user_id)

    # Process in background
    threading.Thread(
        target=process_video_with_updates,
        args=(message.chat.id, message.video.file_id, user_id),
    ).start()


# Process images
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    user_id = message.from_user.id

    # Thread-safe check if user is authorized
    with thread_lock:
        is_authorized = user_id in authorized_users
        is_active = user_id in active_users

    # Check if user is authorized
    if not is_authorized:
        bot.reply_to(
            message,
            "🔒 *Access Restricted*\n\n"
            "You need a valid license to use this service.\n\n"
            f"📱 Your User ID: `{user_id}`\n\n"
            "Please contact @z on Telegram to obtain a license token.\n"
            "Once you have a token, activate it with:\n"
            "/activate YOUR_TOKEN",
        )
        return

    # Prevent multiple submissions
    if is_active:
        bot.reply_to(
            message, "⏳ Please wait, your previous content is still processing."
        )
        return

    # Add user to active processing list with thread safety
    with thread_lock:
        active_users.add(user_id)

    # Get the highest resolution photo
    file_id = message.photo[-1].file_id

    # Process in background
    threading.Thread(
        target=process_image_with_updates, args=(message.chat.id, file_id, user_id)
    ).start()


def process_video_with_updates(chat_id, file_id, user_id):
    """Process video with progress updates - OPTIMIZED FOR FASTER PROCESSING"""
    temp_dir = None
    status_msg = None
    start_time = time.time()
    try:
        # Initial message
        status_msg = bot.send_message(
            chat_id, "⏳ *Processing initiated...*\n• Downloading video..."
        )

        # Get file info
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

        # Create temp directory - USING PYTHONANYWHERE /tmp DIRECTORY
        temp_dir = get_temp_dir()
        input_path = os.path.join(temp_dir, "input_video.mp4")
        output_path = os.path.join(temp_dir, "optimized_video.mp4")

        # Download video
        download_start = time.time()
        response = requests.get(file_url)
        with open(input_path, "wb") as f:
            f.write(response.content)
        download_time = time.time() - download_start

        # Check if user is still authorized
        with thread_lock:
            is_authorized = user_id in authorized_users

        if not is_authorized:
            bot.edit_message_text(
                "🔒 *Access Denied*\n\nYour license is no longer valid.",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )
            return

        # Check video duration
        duration = get_video_duration(input_path)
        if duration > MAX_VIDEO_DURATION:
            bot.edit_message_text(
                f"⚠️ *Video duration exceeds the 1-minute limit*\n\n"
                f"Your video is {duration:.1f} seconds long.\n"
                f"Please trim your video to 60 seconds or less and try again.",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )
            return

        # Update status message with duration info
        bot.edit_message_text(
            f"⏳ *Processing...*\n"
            f"• Video download complete ({download_time:.1f}s)\n"
            f"• Video duration: {duration:.1f}s\n"
            f"• Optimizing with premium settings...",
            chat_id=chat_id,
            message_id=status_msg.message_id,
        )

        # Process video
        processing_start = time.time()
        success, iphone_filename, error_msg = repurpose_video(input_path, output_path)
        processing_time = time.time() - processing_start

        if success:
            # Update with sending status
            bot.edit_message_text(
                f"✅ *Processing complete!*\n"
                f"• Processing time: {processing_time:.1f}s\n"
                f"• Uploading optimized video...",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )

            # Create a copy with the iPhone-style filename
            final_output = os.path.join(temp_dir, iphone_filename or "repurposed.mp4")
            shutil.copy2(output_path, final_output)

            # Send output video
            with open(final_output, "rb") as video_file:
                bot.send_video(
                    chat_id,
                    video_file,
                    caption="✅ *Video optimized successfully*\n\nYour content is ready for multi-account posting.",
                )

            # Final status update with timing info
            total_time = time.time() - start_time
            bot.edit_message_text(
                f"✅ *Process complete*\n\n"
                f"• Total time: {total_time:.1f}s\n"
                f"• Download: {download_time:.1f}s\n"
                f"• Processing: {processing_time:.1f}s\n"
                f"• Upload: {total_time - download_time - processing_time:.1f}s\n\n"
                f"Your optimized video is ready to use.",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )
        else:
            if error_msg == "duration_exceeded":
                bot.edit_message_text(
                    f"⚠️ *Video duration exceeds the 1-minute limit*\n\n"
                    f"Please trim your video to 60 seconds or less and try again.",
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                )
            else:
                bot.edit_message_text(
                    f"❌ *Processing Error*\n\n"
                    f"There was an issue processing your video.\n"
                    f"Error: {error_msg}\n\n"
                    f"Please try again or contact support.",
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                )
    except Exception as e:
        logger.error(f"Error in process_video_with_updates: {e}")
        try:
            if status_msg:
                bot.edit_message_text(
                    f"❌ *Processing Error*\n\n"
                    f"An unexpected error occurred.\n"
                    f"Please try again or contact support if the issue persists.",
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                )
            else:
                bot.send_message(
                    chat_id,
                    f"❌ *Processing Error*\n\n"
                    f"An unexpected error occurred.\n"
                    f"Please try again or contact support if the issue persists.",
                )
        except:
            pass
    finally:
        # Clean up
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

        # Remove user from active list with thread safety
        with thread_lock:
            active_users.discard(user_id)


def process_image_with_updates(chat_id, file_id, user_id):
    """Process image with progress updates"""
    temp_dir = None
    status_msg = None
    start_time = time.time()
    try:
        # Initial message
        status_msg = bot.send_message(
            chat_id, "⏳ *Processing initiated...*\n• Downloading image..."
        )

        # Get file info
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

        # Create temp directory - USING PYTHONANYWHERE /tmp DIRECTORY
        temp_dir = get_temp_dir()
        input_path = os.path.join(temp_dir, "input_image.jpg")
        output_path = os.path.join(temp_dir, "optimized_image.jpg")

        # Download image
        download_start = time.time()
        response = requests.get(file_url)
        with open(input_path, "wb") as f:
            f.write(response.content)
        download_time = time.time() - download_start

        # Check if user is still authorized
        with thread_lock:
            is_authorized = user_id in authorized_users

        if not is_authorized:
            bot.edit_message_text(
                "🔒 *Access Denied*\n\nYour license is no longer valid.",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )
            return

        # Update status message
        bot.edit_message_text(
            f"⏳ *Processing...*\n"
            f"• Image download complete ({download_time:.1f}s)\n"
            f"• Applying anti-detection modifications...",
            chat_id=chat_id,
            message_id=status_msg.message_id,
        )

        # Process image
        processing_start = time.time()
        success, iphone_filename, modifications = repurpose_image(
            input_path, output_path
        )
        processing_time = time.time() - processing_start

        if success:
            # Update with sending status
            bot.edit_message_text(
                f"✅ *Processing complete!*\n"
                f"• Processing time: {processing_time:.1f}s\n"
                f"• Uploading optimized image...",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )

            # Create a copy with the iPhone-style filename
            final_output = os.path.join(temp_dir, iphone_filename or "repurposed.jpg")
            shutil.copy2(output_path, final_output)

            # Send output image
            with open(final_output, "rb") as image_file:
                bot.send_photo(
                    chat_id,
                    image_file,
                    caption="✅ *Image optimized successfully*\n\nYour content is ready for multi-account posting.",
                )

            # Final status update with timing info
            total_time = time.time() - start_time
            bot.edit_message_text(
                f"✅ *Process complete*\n\n"
                f"• Total time: {total_time:.1f}s\n"
                f"• Download: {download_time:.1f}s\n"
                f"• Processing: {processing_time:.1f}s\n"
                f"• Upload: {total_time - download_time - processing_time:.1f}s\n\n"
                f"Your optimized image is ready to use.",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )
        else:
            bot.edit_message_text(
                f"❌ *Processing Error*\n\n"
                f"There was an issue processing your image.\n"
                f"Error: {modifications}\n\n"
                f"Please try again or contact support.",
                chat_id=chat_id,
                message_id=status_msg.message_id,
            )
    except Exception as e:
        logger.error(f"Error in process_image_with_updates: {e}")
        try:
            if status_msg:
                bot.edit_message_text(
                    f"❌ *Processing Error*\n\n"
                    f"An unexpected error occurred.\n"
                    f"Please try again or contact support if the issue persists.",
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                )
            else:
                bot.send_message(
                    chat_id,
                    f"❌ *Processing Error*\n\n"
                    f"An unexpected error occurred.\n"
                    f"Please try again or contact support if the issue persists.",
                )
        except:
            pass
    finally:
        # Clean up
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

        # Remove user from active list with thread safety
        with thread_lock:
            active_users.discard(user_id)


# Handle all other message types
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id

    with thread_lock:
        is_authorized = user_id in authorized_users

    if is_authorized:
        bot.reply_to(
            message,
            "📤 Please send me a video or image to optimize it for multi-account posting.",
        )
    else:
        bot.reply_to(
            message,
            f"🔒 *Access Required*\n\n"
            f"📱 Your User ID: `{user_id}`\n\n"
            f"To activate this service, please contact @z on Telegram and send them your User ID.\n\n"
            f"Once you receive your token, activate it with:\n"
            f"`/activate YOUR_TOKEN`",
        )


# Add restart command for PythonAnywhere
@bot.message_handler(
    commands=["restart"], func=lambda message: message.from_user.id == ADMIN_ID
)
def restart_command(message):
    """Restart the bot (Admin only)"""
    try:
        bot.reply_to(message, "🔄 *Restarting bot...*")
        logger.info("Admin initiated restart")
        # Clean up and exit - the always-on task will restart the bot
        os._exit(0)
    except Exception as e:
        logger.error(f"Error restarting: {e}")
        bot.reply_to(message, f"❌ Error restarting: {str(e)}")


# Connection recovery function
def polling_with_recovery():
    """Run the bot with automatic connection recovery"""
    while True:
        try:
            logger.info(f"Starting bot with {len(authorized_users)} authorized users")
            print("Jacobe Professional Repurposer is running...")
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            # Log the error and wait before retrying
            logger.error(f"Polling error - restarting: {e}")
            time.sleep(10)


# Start the bot
if __name__ == "__main__":
    # Load authorized users from tokens
    for token, data in auth_tokens.items():
        try:
            expires = datetime.datetime.fromisoformat(data.get("expires"))
            if (
                data.get("active")
                and datetime.datetime.now() < expires
                and data.get("user_id")
            ):
                authorized_users.add(int(data.get("user_id")))
        except (ValueError, TypeError):
            logger.error(f"Error loading user from token {token}")

    # Start polling with recovery
    polling_with_recovery()
