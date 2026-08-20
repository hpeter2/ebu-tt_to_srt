#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import datetime
import os
import re


# Function to parse time into the ASS format (HH:MM:SS.CC)
def parse_time(time_str):
    return time_str[:-1]


# Function to map the region and textStyle to ASS alignment
def map_region_to_alignment(region, textStyle):
    
    # Mapping der horizontalen Ausrichtung (Text Style)
    text_style_alignment_map = {
        'textLeft': 1,   # Left
        'textCenter': 2, # Mid
        'textRight': 3   # Right
    }

    # Mapping der vertikalen Ausrichtung (Region)
    region_alignment_map = {
        'top': 6,     # Top
        'center': 3,  # Mid
        'bottom': 0   # Bottom
    }
    
    # Hole die vertikale Ausrichtung basierend auf region
    vertical_alignment = region_alignment_map.get(region, 0)  # Standard: Bottom
    
    # Hole die horizontale Ausrichtung basierend auf textStyle
    horizontal_alignment = text_style_alignment_map.get(textStyle, 2)  # Standard: Center
    
    # Berechne den finalen Wert für \an, der eine Kombination aus vertikal und horizontal ist
    return (vertical_alignment + horizontal_alignment)



def ebu_color_to_ass(color, default="&H00000000"):
    """Convert EBU-TT #RRGGBB or #RRGGBBAA to ASS &HAABBGGRR."""
    if not color:
        return default

    color = color.strip().lstrip('#')

    if len(color) == 6:
        rr, gg, bb = color[0:2], color[2:4], color[4:6]
        aa = "00"  # fully opaque in ASS
    elif len(color) == 8:
        rr, gg, bb, alpha = color[0:2], color[2:4], color[4:6], color[6:8]

        # EBU-TT alpha: 00 = transparent, FF = opaque.
        # ASS alpha: FF = transparent, 00 = opaque.
        aa = f"{255 - int(alpha, 16):02X}"
    else:
        raise ValueError(f"Invalid EBU-TT color: {color!r}")

    # ASS stores colors as AABBGGRR.
    return f"&H{aa}{bb}{gg}{rr}"


def ebu_font_size_to_ass(font_size, play_res_y=1080):
    """
    Convert a simple EBU-TT percentage font size to an approximate ASS size.

    The supplied ARD EBU-TT file uses 160%. Keep the existing 36pt fallback
    for values that cannot be mapped directly.
    """
    if not font_size:
        return 36

    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)%\s*", font_size)
    if not match:
        return 36

    # 160% in this source corresponds visually to the existing 36px-ish
    # ASS subtitle size. Scale proportionally for other percentages.
    return round(36 * float(match.group(1)) / 160)


def generate_ass_header(root, title, namespaces):
    """Build the ASS header from the EBU-TT styles in the source XML."""
    styles = {}

    for style in root.findall('.//tt:head/tt:styling/tt:style', namespaces):
        style_id = style.get('{http://www.w3.org/XML/1998/namespace}id')
        if not style_id:
            continue
        styles[style_id] = style.attrib

    default = styles.get('defaultStyle', {})
    font_size = ebu_font_size_to_ass(default.get('{http://www.w3.org/ns/ttml#styling}fontSize'))
    font_family = default.get('{http://www.w3.org/ns/ttml#styling}fontFamily', 'Arial')
    font_family = font_family.split(',')[0].strip() or 'Arial'

    style_lines = [
        f"Style: Default, {font_family}, {font_size}, "
        "&H00FFFFFF, &H00FFFFFF, &H00000000, &H00000000, "
        "-1, 0, 0, 0, 100, 100, 0, 0, 3, 0, 0, 2, 10, 10, 10, 1"
    ]

    for style_id, attrs in styles.items():
        if style_id in ('defaultStyle', 'textCenter', 'textLeft', 'textRight'):
            continue

        color = attrs.get('{http://www.w3.org/ns/ttml#styling}color', '#FFFFFF')
        background = attrs.get('{http://www.w3.org/ns/ttml#styling}backgroundColor')

        primary = ebu_color_to_ass(color, '&H00FFFFFF')
        back = ebu_color_to_ass(background, '&HFF000000')  # transparent

        # BorderStyle 3 makes BackColour an opaque/semitransparent rectangle
        # behind each rendered line. No outline is used.
        style_lines.append(
            f"Style: {style_id}, {font_family}, {font_size}, "
            f"{primary}, {primary}, &H00000000, {back}, "
            "-1, 0, 0, 0, 100, 100, 0, 0, 3, 0, 0, 2, 10, 10, 10, 1"
        )

    return f"""[Script Info]
Title: {title}
Original Script: WDR mediagroup GmbH
Script Type: V4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{chr(10).join(style_lines)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# Function to create an ASS file from the XML data
def convert_ebut_to_ass(xml_file, ass_file, title):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    namespaces = {
        'tt': 'http://www.w3.org/ns/ttml',
        'ebuttm': 'urn:ebu:tt:metadata'
    }

    # Generate the ASS header/styles from the EBU-TT styling information.
    ass_header = generate_ass_header(root, title, namespaces)

    ass_events = []
    subtitle_number = 1

    for p in root.findall('.//tt:body/tt:div/tt:p', namespaces):
        begin_time = p.get('begin')
        end_time = p.get('end')

        begin_time = parse_time(begin_time)
        end_time = parse_time(end_time)

        style = 'defaultStyle'  # p.get('style', 'defaultStyle')
        span_style = 'Default'
        region = p.get('region', 'bottom')
        textStyle = p.get('style', 'textCenter')
        alignment = "{\\an" + str(map_region_to_alignment(region, textStyle)) + "}"

        text_lines = []
        for span in p.findall('.//tt:span', namespaces):
            span_style = span.get('style', style)
            text = span.text.strip() if span.text else ''
            text_lines.append(text)

        subtitle_text = '\\N'.join(text_lines) # Newline in ASS format

        ass_events.append(f"Dialogue: 0,{begin_time},{end_time},{span_style},{subtitle_number},50,50,50,,{alignment}{subtitle_text}\n")
        subtitle_number += 1

    with open(ass_file, 'w', encoding='utf-8') as f:
        f.write(ass_header + ''.join(ass_events))


# Function to recursively scan a directory for XML files and convert each to ASS format
def convert_folder_to_ass(folder_path):
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if file_name.endswith('.xml'):
                xml_file_path = os.path.join(root, file_name)
                ass_file_name = os.path.splitext(file_name)[0] + '.ass'
                ass_file_path = os.path.join(root, ass_file_name)
                print(xml_file_path)

                # Extract title from file name for ASS header
                title = os.path.splitext(file_name)[0]
                convert_ebut_to_ass(xml_file_path, ass_file_path, title)


# Usage
if __name__ == "__main__":
    convert_folder_to_ass('.')
