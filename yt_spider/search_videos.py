import json
import os
import re
import time
from datetime import UTC, datetime
from typing import Dict, List
from urllib.parse import quote_plus

import pandas as pd
from common import fetch_page_source

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def extract_video_data_from_search(page_source: str) -> List[Dict]:
    """Extract video URLs and metadata from YouTube search results page."""
    initial_data_match = re.search(
        r"var ytInitialData\s*=\s*({.+?});", page_source, re.DOTALL
    )

    if not initial_data_match:
        return []

    try:
        initial_data = json.loads(initial_data_match.group(1))
    except json.JSONDecodeError:
        return []

    videos = []

    # Navigate to search results
    contents = (
        initial_data.get("contents", {})
        .get("twoColumnSearchResultsRenderer", {})
        .get("primaryContents", {})
        .get("sectionListRenderer", {})
        .get("contents", [])
    )

    for content in contents:
        item_section = content.get("itemSectionRenderer", {})
        items = item_section.get("contents", [])

        for item in items:
            # Check for video renderer
            video_renderer = item.get("videoRenderer")
            if not video_renderer:
                continue

            video_id = video_renderer.get("videoId", "")
            if not video_id:
                continue

            # Extract title
            title_runs = video_renderer.get("title", {}).get("runs", [])
            title = title_runs[0].get("text", "") if title_runs else ""

            # Extract channel name
            owner_text = video_renderer.get("ownerText", {}).get("runs", [])
            channel_name = owner_text[0].get("text", "") if owner_text else ""

            # Extract view count
            view_count_text = video_renderer.get("viewCountText", {})
            view_count = view_count_text.get("simpleText", "")
            if not view_count:
                runs = view_count_text.get("runs", [])
                view_count = runs[0].get("text", "") if runs else ""

            # Extract published time
            published_time_text = video_renderer.get("publishedTimeText", {})
            published_time = published_time_text.get("simpleText", "")

            # Extract length
            length_text = video_renderer.get("lengthText", {})
            length = length_text.get("simpleText", "")

            # Extract thumbnail
            thumbnails = video_renderer.get("thumbnail", {}).get(
                "thumbnails", []
            )
            thumbnail_url = thumbnails[-1].get("url", "") if thumbnails else ""

            # Extract description snippet
            description_snippet = video_renderer.get(
                "detailedMetadataSnippets", []
            )
            description = ""
            if description_snippet:
                snippet_runs = (
                    description_snippet[0]
                    .get("snippetText", {})
                    .get("runs", [])
                )
                description = "".join(
                    [run.get("text", "") for run in snippet_runs]
                )

            # Extract badges (e.g., LIVE, NEW, etc.)
            badges = video_renderer.get("badges", [])
            badge_labels = []
            for badge in badges:
                label = badge.get("metadataBadgeRenderer", {}).get("label", "")
                if label:
                    badge_labels.append(label)

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            videos.append(
                {
                    "video_id": video_id,
                    "url": video_url,
                    "title": title,
                    "channel_name": channel_name,
                    "view_count": view_count,
                    "published_time": published_time,
                    "length": length,
                    "thumbnail_url": thumbnail_url,
                    "description_snippet": description,
                    "badges": ", ".join(badge_labels),
                }
            )

    return videos


def search_youtube(query: str) -> List[Dict]:
    """Search YouTube and return video metadata."""
    encoded_query = quote_plus(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

    try:
        page_source = fetch_page_source(search_url)
        videos = extract_video_data_from_search(page_source)
        return videos
    except Exception as e:
        print(f"  ✗ Error searching for '{query}': {str(e)[:100]}")
        return []


def main():
    start_ts = datetime.now(UTC).isoformat()
    print(f"Starting at {start_ts}")

    # Read search queries from CSV
    try:
        search_queries_file = os.path.join(
            BASE_DIR, "input", "search_queries.csv"
        )
        print(f"Reading search queries from {search_queries_file}")
        queries_df = pd.read_csv(search_queries_file)
        if "query" not in queries_df.columns:
            print("Error: CSV file must contain a 'query' column")
            return
        queries = queries_df["query"].tolist()
    except FileNotFoundError:
        print("Error: search_queries.csv file not found")
        print("Please create a search_queries.csv file with a 'query' column")
        return
    except Exception as e:
        print(f"Error reading search_queries.csv: {e}")
        return

    if not queries:
        print("No queries found in search_queries.csv")
        return

    print(f"Found {len(queries)} search queries to process\n")

    all_results = []
    failed_queries = []

    for idx, query in enumerate(queries, 1):
        print(f"[{idx}/{len(queries)}] Searching: {query}")

        try:
            videos = search_youtube(query)

            if videos:
                # Add search query to each result
                for video in videos:
                    video["search_query"] = query
                all_results.extend(videos)
                print(f"  ✓ Found {len(videos)} videos")
            else:
                print("  ⚠ No videos found")
                failed_queries.append({"query": query, "error": "No results"})

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
            failed_queries.append({"query": query, "error": str(e)[:200]})

        # Delay to avoid rate limiting
        if idx < len(queries):
            time.sleep(2)

    # Save results
    if all_results:
        df = pd.DataFrame(all_results)

        # Reorder columns
        column_order = [
            "search_query",
            "video_id",
            "url",
            "title",
            "channel_name",
            "view_count",
            "published_time",
            "length",
            "badges",
            "description_snippet",
            "thumbnail_url",
        ]

        df = df[column_order]
        output_file = os.path.join(
            BASE_DIR, "output", f"search_results-{start_ts}.csv"
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"\n✅ Saved {len(df)} videos to {output_file}")
    else:
        print("\n⚠ No videos were found")

    # Save failed queries
    if failed_queries:
        failed_df = pd.DataFrame(failed_queries)
        output_file = os.path.join(
            BASE_DIR, "output", f"failed_queries-{start_ts}.csv"
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        failed_df.to_csv(output_file, index=False)
        print(
            f"⚠ {len(failed_queries)} queries failed - saved to {output_file}"
        )

    # Summary
    print("\n📊 Summary:")
    print(f"   Total queries: {len(queries)}")
    print(f"   Videos found: {len(all_results)}")
    print(f"   Failed queries: {len(failed_queries)}")


if __name__ == "__main__":
    main()
