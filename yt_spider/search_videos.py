import httpx
import json
import re
import pandas as pd
import time
from typing import Optional
import os
from furl import furl
from common import fetch_page_source

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_search_results(url: str) -> list:
    page_source = fetch_page_source(url)
    return []


def main():
    pass


if __name__ == "__main__":
    main()
