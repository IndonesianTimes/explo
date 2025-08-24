#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
google_dork_serpapi.py
Ambil URL hasil dorking Google via SerpAPI.
"""

import os
import math
import time
import requests

def dedupe_preserve_order(items):
    seen = set()
    out = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out

def fetch_serpapi(query, limit, pause=1.5):
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY tidak ditemukan di environment.")

    endpoint = "https://serpapi.com/search.json"
    per_page = 100
    pages = math.ceil(limit / per_page)
    results = []

    for i in range(pages):
        start = i * per_page
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": per_page,
            "start": start
        }
        r = requests.get(endpoint, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        organic = data.get("organic_results", [])
        for item in organic:
            link = item.get("link")
            if link:
                results.append(link)

        if len(results) >= limit:
            break
        time.sleep(pause)

    return results[:limit]

if __name__ == "__main__":
    try:
        query = input("Masukkan query dork: ").strip()
        limit_str = input("Berapa URL yang mau diambil: ").strip()
        try:
            limit = int(limit_str)
        except ValueError:
            limit = 50  # default kalau salah input

        urls = fetch_serpapi(query, limit)
        urls = dedupe_preserve_order([u.strip() for u in urls if u.startswith("http")])

        out_file = "hasil.txt"
        with open(out_file, "w", encoding="utf-8") as f:
            for u in urls:
                f.write(u + "\n")

        print(f"[OK] {len(urls)} URL disimpan di {out_file}")

    except Exception as e:
        print(f"[ERROR] {e}")
