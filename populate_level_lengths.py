#!/usr/bin/env python3
"""
Populate the 'length' category field for all levels using the GDBrowser API.
Exact duration (m:ss) must be set manually via the admin panel per level.
"""

import requests
import time
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
DB_NAME   = os.getenv('MONGODB_DB', 'rtl_database')


def fetch_length_category(level_id) -> str | None:
    try:
        resp = requests.get(
            f"https://gdbrowser.com/api/level/{level_id}",
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and not data.get('error'):
                return data.get('length')
    except Exception as e:
        print(f"    error: {e}")
    return None


def main():
    client = MongoClient(MONGO_URI)
    col    = client[DB_NAME].levels

    to_update = list(col.find(
        {
            "length": {"$exists": False},
            "level_id": {"$exists": True, "$nin": [None, 0, "", "None"]}
        },
        {"_id": 1, "level_id": 1, "name": 1}
    ))

    no_id = col.count_documents({
        "length": {"$exists": False},
        "$or": [
            {"level_id": {"$exists": False}},
            {"level_id": {"$in": [None, 0, "", "None"]}}
        ]
    })

    if no_id:
        print(f"⚠️  Skipping {no_id} level(s) with no GD Level ID\n")

    if not to_update:
        print("✅ All fetchable levels already have length category data!")
        client.close()
        return

    print(f"🔄 Fetching length category for {len(to_update)} levels...\n")
    print("ℹ️  For exact duration (m:ss), edit each level in the admin panel.\n")

    ok = 0; fail = 0

    for i, level in enumerate(to_update, 1):
        level_id   = level['level_id']
        level_name = level.get('name', 'Unknown')
        db_id      = level['_id']

        print(f"[{i}/{len(to_update)}] {level_name} (ID: {level_id}) ... ", end="", flush=True)

        category = fetch_length_category(level_id)

        if category:
            col.update_one({"_id": db_id}, {"$set": {"length": category, "length_updated": datetime.utcnow()}})
            print(f"✅ {category}")
            ok += 1
        else:
            print("⚠️  no data")
            fail += 1

        if i < len(to_update):
            time.sleep(0.4)

    client.close()
    print(f"\n📊 Done — Updated: {ok}  |  Failed: {fail}  |  No ID: {no_id}")
    print("\nNext: set exact duration (m:ss) per level in Admin → Levels → Edit.")


if __name__ == "__main__":
    print("🚀 Fetching GD length categories...\n")
    main()
    print("\n✅ Done!")
