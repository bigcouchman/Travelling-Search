# Internationallia Travellina

This page documents the datasets used in the project, their sources, and their licensing.

## OpenStreetMap Places

- **Source:** [OpenStreetMap](https://www.openstreetmap.org)
- **License:** Open Database License (ODbL) v1.0
- **Coverage:** Tourist attractions and POIs in African cities (e.g., Accra, Lagos, Nairobi)
- **Format:** CSV (cleaned), original via Overpass/OSMnx (GeoJSON / OSM XML)
- **ETL Script:** [`scripts/ingest.py`](../scripts/ingest.py)

### Fields
- `name`: Name of the place
- `tourism`: OSM tourism tag (e.g., "attraction", "viewpoint")
- `geometry`: Latitude/longitude (point or polygon)

## 📅 Update Frequency
- Re-ingested manually as needed (every month during beta)
- Add new location details

## 📘 Notes
- Filtered for POIs with complete `name` and valid geometry.
- Geometry types currently supported: `Point`, `Polygon`.