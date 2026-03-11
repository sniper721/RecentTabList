import json
from datetime import datetime, timezone

# Generate 100 sample levels
levels = []
for i in range(1, 101):
    # Calculate points using the formula: 250 * (0.963655)^(position-1)
    points = round(250 * (0.9636550814213581 ** (i - 1)), 2)
    
    level = {
        "_id": str(i),
        "name": f"Level {i}",
        "creator": "Creator",
        "verifier": "Verifier",
        "position": i,
        "points": points,
        "level_id": str(10000 + i),
        "difficulty": 10,
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "thumbnail_url": "",
        "min_percentage": 100
    }
    levels.append(level)

cache_data = {
    "levels": levels,
    "last_updated": datetime.now(timezone.utc).isoformat()
}

with open('cache_main_levels.json', 'w', encoding='utf-8') as f:
    json.dump(cache_data, f, ensure_ascii=False, indent=2)

print(f"Created cache with {len(levels)} levels")
print("Restart your Flask server now!")
