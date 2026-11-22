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

def parse_iso(iso_str):
    """Parses ISO timestamp string into a timezone-aware datetime object."""
    return datetime.fromisoformat(iso_str)

def convert_activities_to_gpx(input_json_path, output_gpx_path, allowed_activities=None):
    """
    Converts Google Timeline JSON to GPX, filtered by activity types.
    
    :param allowed_activities: List/set of activity types to include (e.g., ["WALKING", "CYCLING"]).
                               Pass None to include all activity segments.
    """
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data if isinstance(data, list) else data.get("semanticSegments", [])

    # Step 1: Collect all timelinePath points first so we can match them to activity time windows
    path_points = []
    for item in segments:
        if "timelinePath" in item:
            for pt in item["timelinePath"]:
                if "point" in pt and "time" in pt:
                    lat, lon = parse_lat_lon(pt["point"])
                    path_points.append({
                        "lat": lat,
                        "lon": lon,
                        "dt": parse_iso(pt["time"]),
                        "time_str": pt["time"]
                    })

    path_points.sort(key=lambda x: x["dt"])

    # Normalize filter list to uppercase
    if allowed_activities:
        allowed_activities = {a.upper() for a in allowed_activities}

    # Set up GPX 1.1 root
    gpx = ET.Element("gpx", {
        "version": "1.1",
        "creator": "Google Timeline Activity Parser",
        "xmlns": "http://topografix.com",
        "xmlns:xsi": "http://w3.org",
        "xsi:schemaLocation": "http://topografix.com http://topografix.com/gpx.xsd"
    })

    exported_tracks = 0

    # Step 2: Process 'activity' segments
    for item in segments:
        if "activity" not in item:
            continue

        activity = item["activity"]
        act_type = activity.get("topCandidate", {}).get("type", "UNKNOWN").upper()

        # Filter by requested activity types
        if allowed_activities and act_type not in allowed_activities:
            continue

        start_str = item.get("startTime")
        end_str = item.get("endTime")
        if not start_str or not end_str:
            continue

        start_dt = parse_iso(start_str)
        end_dt = parse_iso(end_str)

        # Create a dedicated GPX Track for each activity
        trk = ET.SubElement(gpx, "trk")
        ET.SubElement(trk, "name").text = f"{act_type} ({start_str[:10]})"
        ET.SubElement(trk, "type").text = act_type
        trkseg = ET.SubElement(trk, "trkseg")

        track_coords = []

        # Add Activity Start Point
        start_loc = activity.get("start", {}).get("latLng")
        if start_loc:
            lat, lon = parse_lat_lon(start_loc)
            track_coords.append((start_dt, start_str, lat, lon))

        # Add any intermediate timelinePath points that occurred during this activity
        for pt in path_points:
            if start_dt <= pt["dt"] <= end_dt:
                track_coords.append((pt["dt"], pt["time_str"], pt["lat"], pt["lon"]))

        # Add Activity End Point
        end_loc = activity.get("end", {}).get("latLng")
        if end_loc:
            lat, lon = parse_lat_lon(end_loc)
            track_coords.append((end_dt, end_str, lat, lon))

        # Sort chronologically and remove duplicate consecutive timestamps
        track_coords.sort(key=lambda x: x[0])
        
        last_time = None
        for dt, t_str, lat, lon in track_coords:
            if t_str == last_time:
                continue
            trkpt = ET.SubElement(trkseg, "trkpt", {"lat": lat, "lon": lon})
            ET.SubElement(trkpt, "time").text = t_str
            last_time = t_str

        exported_tracks += 1

    # Write pretty XML
    xml_bytes = ET.tostring(gpx, encoding="utf-8")
    pretty_xml = minidom.parseString(xml_bytes).toprettyxml(indent="  ")

    with open(output_gpx_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"Exported {exported_tracks} activity tracks to {output_gpx_path}")

# Usage Example
if __name__ == "__main__":
    # Set to None to export ALL activity types, or specify a list:
    target_activities = ["WALKING", "RUNNING", "CYCLING", "IN_PASSENGER_VEHICLE"]
    
    convert_activities_to_gpx(
        input_json_path="timeline.json",
        output_gpx_path="activities.gpx",
        allowed_activities=target_activities
    )
