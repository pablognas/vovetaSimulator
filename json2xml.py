import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import html
import argparse


def format_label(event, action, guard):
    parts = []

    if event:
        parts.append(event)

    if action:
        parts.append(f"/ {action}()")

    label = " ".join(parts)

    if guard:
        label += f" [{guard}]"

    # escape XML chars
    return html.escape(label)


def prettify_xml(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def json_to_drawio(json_data, diagram_name="FSM"):
    # root structure
    mxfile = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(mxfile, "diagram", name=diagram_name)
    model = ET.SubElement(diagram, "mxGraphModel")
    root = ET.SubElement(model, "root")

    # base cells
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    states = set()

    # collect states
    for t in json_data:
        states.add(t["source_state"])
        states.add(t["destination_state"])

    # create state nodes
    state_ids = {}
    x, y = 200, 200
    dx = 200

    for i, state in enumerate(states):
        sid = f"state_{i}"
        state_ids[state] = sid

        cell = ET.SubElement(root, "mxCell",
                             id=sid,
                             value=state,
                             style="rounded=1;whiteSpace=wrap;html=1;",
                             vertex="1",
                             parent="1")

        ET.SubElement(cell, "mxGeometry",
                      x=str(x + i * dx),
                      y=str(y),
                      width="140",
                      height="40",
                      attrib={"as": "geometry"})

    # initial node
    init_id = "init"
    init_cell = ET.SubElement(root, "mxCell",
                              id=init_id,
                              style="ellipse;shape=startState;",
                              vertex="1",
                              parent="1")

    ET.SubElement(init_cell, "mxGeometry",
                  x="50", y="200",
                  width="30", height="30",
                  attrib={"as": "geometry"})

    edge_count = 0

    for t in json_data:
        src = t["source_state"]
        dst = t["destination_state"]

        event = t.get("event")
        action = t.get("action")
        guard = t.get("guard")

        label = format_label(event, action, guard)

        # initial transition
        if src == "Initial":
            edge = ET.SubElement(root, "mxCell",
                                 id=f"e{edge_count}",
                                 edge="1",
                                 source=init_id,
                                 target=state_ids[dst],
                                 parent="1")
        else:
            edge = ET.SubElement(root, "mxCell",
                                 id=f"e{edge_count}",
                                 value=label,
                                 edge="1",
                                 source=state_ids[src],
                                 target=state_ids[dst],
                                 parent="1")

        ET.SubElement(edge, "mxGeometry", relative="1", attrib={"as": "geometry"})

        edge_count += 1

    return prettify_xml(mxfile)


# -------------------------
# USO
# -------------------------
if __name__ == "__main__":
    # receber nome do arquivo via argparse

    parser = argparse.ArgumentParser(description="Convert JSON FSM to Draw.io XML")
    parser.add_argument("--filename", help="File name (without extension) located in fms_jsons/ directory")
    args = parser.parse_args()

    input_file = f'fsm_jsons/{args.filename}.json'
    output_file = f'xmls/{args.filename}.xml'

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    xml_str = json_to_drawio(data, diagram_name="FSM")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"XML gerado em: {output_file}")