"""Extract the final composited frame of each local recording for its still preview.

Requires ffmpeg and ffprobe on PATH. The recordings themselves are unchanged.
"""
import json
import subprocess
from pathlib import Path

DEMOS = Path(__file__).resolve().parents[1] / 'docs/assets/demos'
for gif in sorted(DEMOS.glob('*.gif')):
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                             '-show_entries', 'stream=nb_frames', '-of', 'json', str(gif)],
                            check=True, capture_output=True, text=True)
    count = int(json.loads(result.stdout)['streams'][0]['nb_frames'])
    if count < 1:
        raise ValueError(f'{gif.name}: no frames')
    poster = gif.with_name(gif.stem + '-poster.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(gif), '-vf',
                    f'select=eq(n\\,{count - 1})', '-frames:v', '1', str(poster)], check=True)
    print(f'{gif.name}: frame {count} → {poster.name}')
