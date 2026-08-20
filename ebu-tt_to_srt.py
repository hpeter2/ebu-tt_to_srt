#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import datetime
import os


# Function to parse time into the ASS format (HH:MM:SS.CC)
def parse_time(time_str):
    return time_str[:-1]


# Function to map the region to ASS alignment
def map_region_to_alignment(region):
    region_alignment_map = {
        'bottom': 2,  # Bottom center
        'top': 6,     # Top center
        'center': 5   # Middle center
    }
    return region_alignment_map.get(region, 2)  # Default to bottom if undefined


# Function to create an ASS file from the XML data
def convert_ebut_to_ass(xml_file, ass_file, title):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    namespaces = {
        'tt': 'http://www.w3.org/ns/ttml',
        'ebuttm': 'urn:ebu:tt:metadata'
    }

    # Define the styles for the ASS file, dynamically inserting the title
    ass_header = f"""[Script Info]
Title: {title}
Original Script: WDR mediagroup GmbH
ScriptType: v4.00
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,32,&H00000000,&H00000000,&H3D000000,&H00000000,-1,0,0,0,125,125,0.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textBlack,Arial,36,&H00000000,&H00000000,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textRed,Arial,36,&H000000FF,&H000000FF,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textGreen,Arial,36,&H0000FF00,&H0000FF00,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textYellow,Arial,36,&H0000FFFF,&H0000FFFF,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textBlue,Arial,36,&H00FF0000,&H00FF0000,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textMagenta,Arial,36,&H00FF00FF,&H00FF00FF,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textCyan,Arial,36,&H00FFFF00,&H00FFFF00,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1
Style: textWhite,Arial,36,&H00FFFFFF,&H00FFFFFF,&H3D000000,&H00000000,-1,0,0,0,125,125,1.00,0.00,3,1.00,0.00,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

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
        alignment = "{\\a" + str(map_region_to_alignment(region)) + "}"

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
