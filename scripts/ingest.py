import overpy
import sqlite3
import requests
import random
from decimal import Decimal

DB_PATH = "database.db"
API = overpy.Overpass()

# Find tourist destinations, gather details
def fetch_osm_pois(lat, lon, radius=5000):
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"="attraction"](around:{radius},{lat},{lon});
      node["tourism"="viewpoint"](around:{radius},{lat},{lon});
    );
    out center;
    """
    return API.query(query)

def seed_osm():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS places (
        id TEXT PRIMARY KEY,
        name TEXT,
        city TEXT,
        lat REAL,
        lng REAL,
        description TEXT,
        image_url TEXT,
        category TEXT,
        rating REAL
    )
    """)
    conn.commit()
    areas = [
        ("Paris, France", 48.8566, 2.3522),
        ("Rome, Italy", 41.9028, 12.4964),
        ("New York, USA", 40.7128, -74.0060),
        ("San Francisco, USA", 37.7749, -122.4194),
        ("London, UK", 51.5074, -0.1278),
        ("Barcelona, Spain", 41.3851, 2.1734),
        ("Sydney, Australia", -33.8688, 151.2093),
        ("Toronto, Canada", 43.651070, -79.347015),
        ("Cape Town, South Africa", -33.9249, 18.4241),
        ("Bangkok, Thailand", 13.7563, 100.5018),
        ("Dubai, UAE", 25.276987, 55.296249),
        ("Berlin, Germany", 52.5200, 13.4050)
    ]

    added = 0
    MAX_PLACES = 100

    for city_name, lat, lon in areas:
        print(f"Fetching places near {city_name}...")
        try:
            res = fetch_osm_pois(lat, lon)
        except Exception as e:
            print(f"Failed to fetch data for {city_name}: {e}")
            continue

        for node in res.nodes:
            if added >= MAX_PLACES:
                break

            tags = node.tags
            place_name_en = tags.get("name:en")
            if not place_name_en:
                continue  # skip if there's no English name
            place_name = place_name_en

            # Filter out non-real locations (if no address info)
            if not any(k.startswith("addr:") for k in tags):
                continue

            # Skip duplicates
            c.execute("SELECT COUNT(*) FROM places WHERE name = ? AND city = ?", (place_name, city_name))
            if c.fetchone()[0] > 0:
                continue

            # Convert lat/lon to float if Decimal
            lat_val = float(node.lat) if isinstance(node.lat, Decimal) else node.lat
            lon_val = float(node.lon) if isinstance(node.lon, Decimal) else node.lon

            # Insert into DB
            # Description (Wikipedia tag text) and image fetching
            wikipedia_tag = tags.get("wikipedia", "")
            image_url = "No Image available"
            description = "No Description available"
            category = (
                "Attraction" if tags.get("tourism") == "attraction" else
                "Viewpoint" if tags.get("tourism") == "viewpoint" else
                "Other"
            )
            rating = round(random.uniform(3.0, 5.0), 1)

            wikipedia_tag = tags.get("wikipedia:en") or tags.get("wikipedia")
            if wikipedia_tag and ":" in wikipedia_tag:
                _, wiki_title = wikipedia_tag.split(":", 1)
                image_url, description = fetch_wikipedia_image_and_description(wiki_title)

            c.execute("""
            INSERT OR IGNORE INTO places (id, name, city, lat, lng, description, image_url, category, rating, cesium_asset_id, )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(node.id),
                place_name,
                city_name,
                lat_val,
                lon_val,
                description,
                image_url,
                category,
                rating
            ))

            print(f"Added: {place_name} ({city_name})")
            added += 1

        conn.commit()

    conn.close()
    print("🌍 OSM data seeding complete.")

# Find wikipdia images for search results
def fetch_wikipedia_image_and_description(title):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            img = data.get("thumbnail", {}).get("source", "No image available")
            desc = data.get("extract", "No description available")
            return img, desc
    except Exception as e:
        print(f"Error fetching Wikipedia data for {title}: {e}")
    
    return "No image available", "No description available"


if __name__ == "__main__":
    seed_osm()
