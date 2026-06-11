#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# rekordbox_exporter.py
# Exports AI-Mixer analysis to Rekordbox XML format for DJ software import.
# Includes BPM, key, cue points, memory points, and playlist data.
# -----------------------------------------------------------------------------

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional
from xml.dom import minidom


# Rekordbox key notation mapping (Camelot wheel compatible)
KEY_TO_REKORDBOX = {
    'C': 1, 'C major': 1, 'Am': 1, 'A minor': 1,
    'G': 2, 'G major': 2, 'Em': 2, 'E minor': 2,
    'D': 3, 'D major': 3, 'Bm': 3, 'B minor': 3,
    'A': 4, 'A major': 4, 'F#m': 4, 'F# minor': 4,
    'E': 5, 'E major': 5, 'C#m': 5, 'C# minor': 5,
    'B': 6, 'B major': 6, 'G#m': 6, 'G# minor': 6,
    'F#': 7, 'F# major': 7, 'D#m': 7, 'D# minor': 7,
    'Db': 8, 'Db major': 8, 'Bbm': 8, 'Bb minor': 8,
    'Ab': 9, 'Ab major': 9, 'Fm': 9, 'F minor': 9,
    'Eb': 10, 'Eb major': 10, 'Cm': 10, 'C minor': 10,
    'Bb': 11, 'Bb major': 11, 'Gm': 11, 'G minor': 11,
    'F': 12, 'F major': 12, 'Dm': 12, 'D minor': 12,
}

# Cue point colors in Rekordbox
CUE_COLORS = {
    'mix_in': '0x28E5FF',   # Cyan
    'drop': '0xFF0000',      # Red
    'mix_out': '0x00FF00',   # Green
    'loop': '0xFFFF00',      # Yellow
    'hot_cue': '0xFF00FF',   # Magenta
}


def time_to_ms(seconds: float) -> int:
    """Convert seconds to milliseconds."""
    return int(seconds * 1000)


def generate_rekordbox_xml(
    analysis_list: List[Dict[str, Any]],
    output_path: str,
    playlist_name: Optional[str] = None,
) -> str:
    """
    Generate Rekordbox XML from AI-Mixer analysis data.

    Args:
        analysis_list: List of track analysis dictionaries from kannada_mashup_analyzer
        output_path: Path to save the XML file
        playlist_name: Optional name for the playlist

    Returns:
        Path to the created XML file
    """
    # Create root element
    root = ET.Element('DJ_PLAYLISTS')
    root.set('Version', '1.0.0')

    # Product info
    product = ET.SubElement(root, 'PRODUCT')
    product.set('Name', 'AI-Mixer')
    product.set('Version', '2.0.0')
    product.set('Company', 'AI-Mixer')

    # Collection (all tracks)
    collection = ET.SubElement(root, 'COLLECTION')
    collection.set('Entries', str(len(analysis_list)))

    track_ids = []

    for idx, analysis in enumerate(analysis_list):
        track_id = str(idx + 1)
        track_ids.append(track_id)

        track = ET.SubElement(collection, 'TRACK')
        track.set('TrackID', track_id)

        # Basic info
        filename = analysis.get('filename', f'track_{idx}.mp3')
        track.set('Name', filename.replace('.mp3', '').replace('_', ' '))
        track.set('Artist', '')

        # File location
        file_path = analysis.get('file_path', '')
        if file_path:
            track.set('Location', f"file://localhost{file_path}")

        # Duration
        duration = analysis.get('duration', 0)
        track.set('TotalTime', str(int(duration)))

        # BPM - from beat_grid or top-level
        bpm = analysis.get('bpm')
        if not bpm and 'beat_grid' in analysis:
            bpm = analysis['beat_grid'].get('tempo')
        if bpm:
            track.set('AverageBpm', f"{float(bpm):.2f}")

        # Key
        key = analysis.get('key', '')
        if key:
            track.set('Tonality', key)
            rekordbox_key = KEY_TO_REKORDBOX.get(key, 0)
            if rekordbox_key:
                track.set('Key', str(rekordbox_key))

        # Energy (Rating in Rekordbox is 0-255, we use 0-5)
        energy = analysis.get('energy', 0)
        if 'emotional_curve' in analysis:
            energy = analysis['emotional_curve'].get('average_intensity', energy)
        rating = int(energy * 5)  # 0-5 scale
        track.set('Rating', str(rating))

        # Genre (use Tala if available)
        tala = analysis.get('tala', {})
        if tala.get('detected_tala'):
            track.set('Genre', f"Kannada - {tala['detected_tala']}")

        # Comments (add analysis summary)
        comments = []
        if tala.get('detected_tala'):
            comments.append(f"Tala: {tala['detected_tala']} ({tala.get('confidence', 0):.0%})")
        if analysis.get('scale_ragam', {}).get('detected_scale'):
            comments.append(f"Scale: {analysis['scale_ragam']['detected_scale']}")
        if comments:
            track.set('Comments', ' | '.join(comments))

        # Tempo info with beat grid
        beat_grid = analysis.get('beat_grid', {})
        if beat_grid:
            tempo_el = ET.SubElement(track, 'TEMPO')
            tempo_el.set('Inizio', '0.0')
            if beat_grid.get('tempo'):
                tempo_el.set('Bpm', f"{float(beat_grid['tempo']):.2f}")
            tempo_el.set('Metro', '4/4')  # Assume 4/4 time
            if beat_grid.get('first_downbeat'):
                tempo_el.set('Battito', str(int(beat_grid['first_downbeat'] * 1000)))

        # Position marks (cue points)
        cue_points = analysis.get('dj_cue_points', {})
        position_mark_num = 0

        # Mix In point (Memory Cue)
        if cue_points.get('mix_in'):
            mix_in = cue_points['mix_in']
            pos = ET.SubElement(track, 'POSITION_MARK')
            pos.set('Name', 'MIX IN')
            pos.set('Type', '0')  # 0 = cue, 1 = fade-in, 2 = fade-out, 3 = load
            pos.set('Start', str(time_to_ms(mix_in.get('time', 0))))
            pos.set('Num', str(position_mark_num))
            pos.set('Red', '40')
            pos.set('Green', '229')
            pos.set('Blue', '255')
            position_mark_num += 1

        # Drop point
        if cue_points.get('drop'):
            drop = cue_points['drop']
            pos = ET.SubElement(track, 'POSITION_MARK')
            pos.set('Name', 'DROP')
            pos.set('Type', '0')
            pos.set('Start', str(time_to_ms(drop.get('time', 0))))
            pos.set('Num', str(position_mark_num))
            pos.set('Red', '255')
            pos.set('Green', '0')
            pos.set('Blue', '0')
            position_mark_num += 1

        # Mix Out point
        if cue_points.get('mix_out'):
            mix_out = cue_points['mix_out']
            pos = ET.SubElement(track, 'POSITION_MARK')
            pos.set('Name', 'MIX OUT')
            pos.set('Type', '0')
            pos.set('Start', str(time_to_ms(mix_out.get('time', 0))))
            pos.set('Num', str(position_mark_num))
            pos.set('Red', '0')
            pos.set('Green', '255')
            pos.set('Blue', '0')
            position_mark_num += 1

        # Loop points
        loop_points = cue_points.get('loop_points', [])
        for i, loop in enumerate(loop_points[:4]):  # Max 4 loops
            pos = ET.SubElement(track, 'POSITION_MARK')
            pos.set('Name', f'LOOP {i+1}')
            pos.set('Type', '4')  # Loop type
            pos.set('Start', str(time_to_ms(loop.get('start', 0))))
            pos.set('End', str(time_to_ms(loop.get('end', 0))))
            pos.set('Num', str(position_mark_num))
            pos.set('Red', '255')
            pos.set('Green', '255')
            pos.set('Blue', '0')
            position_mark_num += 1

        # Hot cues
        hot_cues = cue_points.get('hot_cues', [])
        for cue in hot_cues[:8]:  # Max 8 hot cues
            pos = ET.SubElement(track, 'POSITION_MARK')
            pos.set('Name', cue.get('label', f"Hot Cue {cue.get('number', 0)}"))
            pos.set('Type', '0')
            pos.set('Start', str(time_to_ms(cue.get('time', 0))))
            pos.set('Num', str(position_mark_num))
            pos.set('Red', '255')
            pos.set('Green', '0')
            pos.set('Blue', '255')
            position_mark_num += 1

    # Playlists
    playlists = ET.SubElement(root, 'PLAYLISTS')
    root_folder = ET.SubElement(playlists, 'NODE')
    root_folder.set('Type', '0')  # Folder
    root_folder.set('Name', 'ROOT')
    root_folder.set('Count', '1')

    # Create playlist
    playlist = ET.SubElement(root_folder, 'NODE')
    playlist.set('Type', '1')  # Playlist
    playlist.set('Name', playlist_name or f'AI-Mixer Export {datetime.now().strftime("%Y-%m-%d")}')
    playlist.set('KeyType', '0')
    playlist.set('Entries', str(len(track_ids)))

    for track_id in track_ids:
        track_ref = ET.SubElement(playlist, 'TRACK')
        track_ref.set('Key', track_id)

    # Format and write XML
    xml_string = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ')

    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    final_xml = '\n'.join(lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_xml)

    return output_path


def generate_serato_crates(
    analysis_list: List[Dict[str, Any]],
    output_dir: str,
    crate_name: str = "AI-Mixer"
) -> str:
    """
    Generate Serato-compatible crate file.
    Note: Serato uses .crate files with specific binary format.
    This creates a simplified M3U playlist that Serato can import.

    Args:
        analysis_list: List of track analysis dictionaries
        output_dir: Directory to save the crate file
        crate_name: Name for the crate

    Returns:
        Path to the created file
    """
    os.makedirs(output_dir, exist_ok=True)

    # Create M3U playlist (Serato can import this)
    output_path = os.path.join(output_dir, f"{crate_name}.m3u")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        f.write(f'# AI-Mixer Export - {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')

        for analysis in analysis_list:
            file_path = analysis.get('file_path', '')
            filename = analysis.get('filename', 'Unknown')
            duration = int(analysis.get('duration', 0))

            # EXTINF line with duration and title
            f.write(f'#EXTINF:{duration},{filename.replace(".mp3", "")}\n')
            f.write(f'{file_path}\n')

    return output_path


def export_analysis_json(
    analysis_list: List[Dict[str, Any]],
    output_path: str,
) -> str:
    """
    Export analysis data as JSON for other DJ software or custom tools.

    Args:
        analysis_list: List of track analysis dictionaries
        output_path: Path to save the JSON file

    Returns:
        Path to the created JSON file
    """
    import json

    export_data = {
        "version": "2.0.0",
        "exported_at": datetime.now().isoformat(),
        "track_count": len(analysis_list),
        "tracks": []
    }

    for analysis in analysis_list:
        track_data = {
            "filename": analysis.get('filename'),
            "file_path": analysis.get('file_path'),
            "duration": analysis.get('duration'),
            "bpm": analysis.get('bpm') or analysis.get('beat_grid', {}).get('tempo'),
            "key": analysis.get('key'),
            "energy": analysis.get('energy'),
            "tala": analysis.get('tala', {}).get('detected_tala'),
            "scale": analysis.get('scale_ragam', {}).get('detected_scale'),
            "cue_points": analysis.get('dj_cue_points', {}),
            "structure": analysis.get('structure', []),
            "sections": analysis.get('section_classification', []),
        }
        export_data["tracks"].append(track_data)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)

    return output_path


if __name__ == "__main__":
    # Test with sample data
    sample_analysis = [
        {
            "filename": "test_song.mp3",
            "file_path": "/path/to/test_song.mp3",
            "duration": 240,
            "bpm": 120.5,
            "key": "A minor",
            "energy": 0.7,
            "beat_grid": {
                "tempo": 120.5,
                "first_downbeat": 0.25,
            },
            "tala": {
                "detected_tala": "adi_tala",
                "confidence": 0.85,
            },
            "dj_cue_points": {
                "mix_in": {"time": 16.0, "reason": "intro end"},
                "drop": {"time": 64.0, "reason": "energy peak"},
                "mix_out": {"time": 200.0, "reason": "outro start"},
                "loop_points": [
                    {"start": 32.0, "end": 48.0},
                    {"start": 96.0, "end": 112.0},
                ],
                "hot_cues": [
                    {"number": 1, "time": 0.0, "label": "Intro"},
                    {"number": 2, "time": 64.0, "label": "Drop"},
                ],
            }
        }
    ]

    output_path = "/tmp/test_rekordbox.xml"
    result = generate_rekordbox_xml(sample_analysis, output_path)
    print(f"Generated: {result}")

    with open(result, 'r') as f:
        print(f.read())
