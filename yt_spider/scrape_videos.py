import json
import os
import re
import time
from datetime import datetime, UTC
from typing import Optional

import httpx
import pandas as pd

from common import fetch_page_source

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def extract_details(page_source: str) -> Optional[dict]:
    # Extract ytInitialPlayerResponse JSON object
    player_response_match = re.search(
        r"var ytInitialPlayerResponse\s*=\s*({.+?});", page_source, re.DOTALL
    )

    if not player_response_match:
        raise ValueError(
            "Could not find ytInitialPlayerResponse in page source"
        )

    player_data = json.loads(player_response_match.group(1))

    # Extract ytInitialData JSON object for engagement panels
    initial_data_match = re.search(
        r"var ytInitialData\s*=\s*({.+?});", page_source, re.DOTALL
    )

    comments_count = None
    if initial_data_match:
        try:
            initial_data = json.loads(initial_data_match.group(1))

            # Navigate through the JSON structure to find engagement panels
            engagement_panels = initial_data.get("engagementPanels", [])

            # Find the comments panel
            for panel in engagement_panels:
                panel_renderer = panel.get(
                    "engagementPanelSectionListRenderer", {}
                )
                header = panel_renderer.get("header", {})
                title_header = header.get(
                    "engagementPanelTitleHeaderRenderer", {}
                )

                # Check if this is the comments panel
                title = title_header.get("title", {})
                title_runs = title.get("runs", [])

                if title_runs and title_runs[0].get("text") == "Comments":
                    # Extract comment count from contextualInfo
                    contextual_info = title_header.get("contextualInfo", {})
                    info_runs = contextual_info.get("runs", [])
                    if info_runs:
                        comments_count = info_runs[0].get("text", "0")
                    break
        except Exception:
            # If parsing fails, keep default value
            pass

    # Extract video details
    video_details = player_data.get("videoDetails", {})
    microformat = player_data.get("microformat", {}).get(
        "playerMicroformatRenderer", {}
    )

    # Extract data
    video_id = video_details.get("videoId", "")
    title = video_details.get("title", "")
    description = video_details.get("shortDescription", "")
    length_seconds = video_details.get("lengthSeconds", "0")
    keywords = ", ".join(video_details.get("keywords", []))
    channel_id = video_details.get("channelId", "")
    channel_name = video_details.get("author", "")

    # Engagement metrics from microformat
    view_count = microformat.get("viewCount", "0")
    like_count = microformat.get("likeCount", "0")

    # Additional metadata
    category = microformat.get("category", "")
    publish_date = microformat.get("publishDate", "")
    upload_date = microformat.get("uploadDate", "")
    is_unlisted = microformat.get("isUnlisted", False)

    # Video quality info
    formats = player_data.get("streamingData", {}).get("formats", [])
    adaptive_formats = player_data.get("streamingData", {}).get(
        "adaptiveFormats", []
    )

    # Get highest quality video format
    max_quality = ""
    max_fps = 0
    if adaptive_formats:
        for fmt in adaptive_formats:
            if "qualityLabel" in fmt:
                quality_label = fmt.get("qualityLabel", "")
                fps = fmt.get("fps", 0)
                if fps > max_fps or (
                    fps == max_fps and quality_label > max_quality
                ):
                    max_quality = quality_label
                    max_fps = fps

    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "views": view_count,
        "likes": like_count,
        "comments": comments_count,
        "length_seconds": length_seconds,
        "keywords": keywords,
        "category": category,
        "publish_date": publish_date,
        "upload_date": upload_date,
        "is_unlisted": is_unlisted,
        "max_quality": max_quality,
        "max_fps": max_fps,
    }


def main():
    start_ts = datetime.now(UTC).isoformat()
    print(f"Starting at {start_ts}")

    # Read URLs from CSV file
    try:
        search_results_file = os.path.join(
            BASE_DIR, "input", "search_results.csv"
        )
        print(f"Reading search results from {search_results_file}")
        urls_df = pd.read_csv(search_results_file)
        if "url" not in urls_df.columns:
            raise ValueError("CSV file must contain a 'url' column")
        urls = urls_df["url"].tolist()
        urls = list(set(urls))
    except FileNotFoundError:
        print("Error: urls.csv file not found")
        print(
            "Please create a urls.csv file with a 'url' column containing YouTube Shorts URLs"
        )
        return
    except Exception as e:
        print(f"Error reading urls.csv: {e}")
        return

    if not urls:
        print("No URLs found in urls.csv")
        return

    print(f"Found {len(urls)} unique URLs to process\n")

    # Define column order for output
    column_order = [
        "url",
        "video_id",
        "title",
        "channel_name",
        "channel_id",
        "views",
        "likes",
        "comments",
        "length_seconds",
        "category",
        "publish_date",
        "upload_date",
        "is_unlisted",
        "max_quality",
        "max_fps",
        "keywords",
        "description",
    ]

    results = []
    failed_urls = []
    save_interval = 10  # Save progress every N URLs

    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] Fetching: {url}")

        try:
            page_source = fetch_page_source(url)
            details = extract_details(page_source)

            if details:
                details["url"] = url
                results.append(details)
                print(f"  ✓ Extracted: {details['title'][:50]}...")
            else:
                print("  ✗ Failed to extract details")
                failed_urls.append({"url": url, "error": "Extraction failed"})

        except httpx.TimeoutException:
            print("  ✗ Timeout error - skipping")
            failed_urls.append({"url": url, "error": "Timeout"})
        except httpx.HTTPStatusError as e:
            print(f"  ✗ HTTP {e.response.status_code} error - skipping")
            failed_urls.append(
                {"url": url, "error": f"HTTP {e.response.status_code}"}
            )
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]} - skipping")
            failed_urls.append({"url": url, "error": str(e)[:200]})

        # Periodic saving to prevent data loss
        if results and idx % save_interval == 0:
            temp_df = pd.DataFrame(results)
            temp_df = (
                temp_df[column_order]
                if all(col in temp_df.columns for col in column_order)
                else temp_df
            )
            output_file = os.path.join(
                BASE_DIR, "output", f"yt_videos_progress-{start_ts}.csv"
            )
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            temp_df.to_csv(output_file, index=False)
            print(
                f"  💾 Progress saved ({len(results)} videos to {output_file})"
            )

        # Small delay to avoid rate limiting
        if idx < len(urls):
            time.sleep(1)

    # Save successful results
    if results:
        df = pd.DataFrame(results)
        df = df[column_order]
        output_file = os.path.join(
            BASE_DIR, "output", f"yt_videos-{start_ts}.csv"
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"\n✅ Successfully saved {len(df)} videos to {output_file}")
    else:
        print("\n⚠ No videos were successfully extracted")

    # Save failed URLs for retry
    if failed_urls:
        failed_df = pd.DataFrame(failed_urls)
        output_file = os.path.join(
            BASE_DIR, "output", f"failed_urls-{start_ts}.csv"
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        failed_df.to_csv(output_file, index=False)
        print(f"⚠ {len(failed_urls)} URLs failed - saved to {output_file}")

    # Summary
    print("\n📊 Summary:")
    print(f"   Total URLs: {len(urls)}")
    print(f"   Successful: {len(results)}")
    print(f"   Failed: {len(failed_urls)}")
    print(f"   Success rate: {len(results)/len(urls)*100:.1f}%")


if __name__ == "__main__":
    main()
