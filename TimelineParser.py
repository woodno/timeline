import json
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

def parse_lat_lng(coord_str):
    """Cleans and extracts floating-point numbers from strings like '-26.7577793°, 153.1249247°'"""
    # Remove degree symbols and match float values
    clean_str = coord_str.replace('°', '')
    matches = re.findall(r'[-+]?\d*\.\d+|\d+', clean_str)
    if len(matches) == 2:
        return float(matches[0]), float(matches[1])
    return None

def json_to_gml(json_data, output_file_path):
    # Setup the base GML / OGC namespaces
    gml_ns = "http://opengis.net"
    ET.register_namespace('gml', gml_ns)
    
    # Create the root GML FeatureCollection
    root = ET.Element(f"{{{gml_ns}}}FeatureCollection")
    root.set(f"{{{gml_ns}}}id", "GoogleTimelineExport")
    
    segments = json_data.get("semanticSegments", [])
    
    for idx, segment in enumerate(segments):
        # 1. Extract and convert LineString paths
        if "timelinePath" in segment:
            coords = []
            for item in segment["timelinePath"]:
                parsed = parse_lat_lng(item.get("point", ""))
                if parsed:
                    coords.append(f"{parsed[0]} {parsed[1]}")
            
            if coords:
                # Build GML structure for a LineString feature
                member = ET.SubElement(root, f"{{{gml_ns}}}featureMember")
                line_feat = ET.SubElement(member, f"{{{gml_ns}}}LineString")
                line_feat.set(f"{{{gml_ns}}}id", f"path_{idx}")
                
                pos_list = ET.SubElement(line_feat, f"{{{gml_ns}}}posList")
                pos_list.text = " ".join(coords)
                
        # 2. Extract and convert Visit / Parking Point locations
        visit_point = None
        if "visit" in segment:
            loc = segment["visit"].get("topCandidate", {}).get("placeLocation", {}).get("latLng", "")
            visit_point = parse_lat_lng(loc)
        elif "activity" in segment and "parking" in segment["activity"]:
            loc = segment["activity"]["parking"].get("location", {}).get("latLng", "")
            visit_point = parse_lat_lng(loc)
            
        if visit_point:
            # Build GML structure for a Point feature
            member = ET.SubElement(root, f"{{{gml_ns}}}featureMember")
            point_feat = ET.SubElement(member, f"{{{gml_ns}}}Point")
            point_feat.set(f"{{{gml_ns}}}id", f"point_{idx}")
            
            pos = ET.SubElement(point_feat, f"{{{gml_ns}}}pos")
            pos.text = f"{visit_point[0]} {visit_point[1]}"

    # Pretty-print and save XML code
    xml_str = ET.tostring(root, encoding='utf-8')
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

# --- EXECUTION ---

# Your input JSON sample data (fixed to valid trailing syntax)
raw_json_string = """
{
  "semanticSegments": [
    {
      "startTime": "2026-04-12T06:00:00.000+10:00",
      "endTime": "2026-04-12T08:00:00.000+10:00",
      "timelinePath": [
        { "point": "-26.7577793°, 153.1249247°", "time": "2026-04-12T06:33:00.000+10:00" },
        { "point": "-26.7528128°, 153.1286057°", "time": "2026-04-12T07:58:00.000+10:00" }
      ]
    },
    {
      "startTime": "2026-04-12T06:33:13.000+10:00",
      "endTime": "2026-04-12T08:08:18.000+10:00",
      "activity": {
        "parking": {
          "location": { "latLng": "-26.7353828°, 153.1254706°" }
        }
      }
    },
    {
      "startTime": "2026-04-12T08:00:00.000+10:00",
      "endTime": "2026-04-12T10:00:00.000+10:00",
      "timelinePath": [
        { "point": "-26.7353828°, 153.1254706°", "time": "2026-04-12T08:08:00.000+10:00" },
        { "point": "-26.735531°, 153.1282885°", "time": "2026-04-12T08:32:00.000+10:00" }
      ]
    },
    {
      "startTime": "2026-04-12T08:08:18.000+10:00",
      "endTime": "2026-04-12T10:26:21.000+10:00",
      "visit": {
        "topCandidate": {
          "placeLocation": { "latLng": "-26.7353852°, 153.1258095°" }
        }
      }
    }
  ]
}
"""

data = json.loads(raw_json_string)
json_to_gml(data, "timeline_output.gml")
print("Conversion complete! Check 'timeline_output.gml'.")
