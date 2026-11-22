import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
#Taken from AI conversation at
#https://share.google/aimode/ETXjdDdrEEPGz31GG
def parse_lat_lon(coord_str):
    """Converts '46.5158807°, 6.6268572°' into ('46.5158807', '6.6268572')."""
    lat, lon = coord_str.replace("°", "").split(",")
    return lat.strip(), lon.strip()

def format_gpx_time(iso_str):
    """Normalizes ISO timestamp with timezone offset to standard GPX format."""
    dt = datetime.fromisoformat(iso_str)
    return dt.isoformat()

def convert_timeline_to_gpx(input_json_path, output_gpx_path):
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both a root list [...] or a dict containing {"semanticSegments": [...]}
    segments = data if isinstance(data, list) else data.get("semanticSegments", [])

    # Set up GPX 1.1 root element
    gpx = ET.Element("gpx", {
        "version": "1.1",
        "creator": "Google Timeline JSON to GPX Parser",
        "xmlns": "http://topografix.com",
        "xmlns:xsi": "http://w3.org",
        "xsi:schemaLocation": "http://topografix.com http://topografix.com/gpx.xsd"
    })

    # Create a single Track and Track Segment for timelinePath points
    trk = ET.SubElement(gpx, "trk")
    ET.SubElement(trk, "name").text = "Google Timeline Path"
    trkseg = ET.SubElement(trk, "trkseg")

    all_track_points = []

    for item in segments:
        # 1. Extract 'timelinePath' entries -> GPX Track Points (<trkpt>)
        if "timelinePath" in item:
            for pt in item["timelinePath"]:
                if "point" in pt and "time" in pt:
                    lat, lon = parse_lat_lon(pt["point"])
                    all_track_points.append({
                        "lat": lat,
                        "lon": lon,
                        "time": format_gpx_time(pt["time"])
                    })

        # 2. Extract 'visit' entries -> GPX Waypoints (<wpt>)
        if "visit" in item:
            candidate = item["visit"].get("topCandidate", {})
            loc_str = candidate.get("placeLocation", {}).get("latLng")
            if loc_str:
                lat, lon = parse_lat_lon(loc_str)
                wpt = ET.SubElement(gpx, "wpt", {"lat": lat, "lon": lon})
                
                if "startTime" in item:
                    ET.SubElement(wpt, "time").text = format_gpx_time(item["startTime"])
                
                semantic_type = candidate.get("semanticType", "Visit")
                place_id = candidate.get("placeId", "")
                ET.SubElement(wpt, "name").text = f"{semantic_type} ({place_id})"

    # Sort track points chronologically before writing
    all_track_points.sort(key=lambda x: x["time"])

    for pt in all_track_points:
        trkpt = ET.SubElement(trkseg, "trkpt", {"lat": pt["lat"], "lon": pt["lon"]})
        ET.SubElement(trkpt, "time").text = pt["time"]

    # Format and write pretty XML
    xml_bytes = ET.tostring(gpx, encoding="utf-8")
    pretty_xml = minidom.parseString(xml_bytes).toprettyxml(indent="  ")

    with open(output_gpx_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"Successfully exported {len(all_track_points)} track points to {output_gpx_path}")

# Usage
if __name__ == "__main__":
    convert_timeline_to_gpx("timeline.json", "output.gpx")
