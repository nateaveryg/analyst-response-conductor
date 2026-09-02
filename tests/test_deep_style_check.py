"""Detailed analysis script for checking all Google style, grammar, and notes rules."""

import json
import re
import subprocess

PRES_ID = "1EXtNoj3Hp9G2WlBH3dkTaLmc8Jb9cZdpDkH3KpLBg3Q"

def run_cmd(cmd):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nStderr: {res.stderr}")
    return res.stdout

def main():
    slides_json = json.loads(run_cmd(["gslides", "list-slides", PRES_ID, "--json"]))
    print(f"Total slides: {len(slides_json)}")

    for i, slide in enumerate(slides_json, 1):
        s_id = slide["objectId"]
        notes = run_cmd(["gslides", "get-notes", PRES_ID, "--slide", s_id]).strip()
        
        # Check notes lines
        print(f"\n================ SLIDE {i} ({s_id}) ================")
        # Get page elements
        page_info = json.loads(run_cmd(["gslides", "get-page", PRES_ID, s_id, "--json"]))
        
        elements_text = []
        for elem in page_info.get("pageElements", []):
            shape = elem.get("shape", {})
            text_elem = shape.get("text", {})
            for tr in text_elem.get("textElements", []):
                content = tr.get("textRun", {}).get("content", "")
                if content.strip():
                    elements_text.append(content.strip())
        
        full_slide_text = "\n".join(elements_text)
        
        # Check forbidden words
        for target, repl in [
            (r'\bnative\b', "built-in"),
            (r'\bmaster\b', "primary"),
            (r'\bslave\b', "secondary"),
            (r'\bwhitelist\b', "allowlist"),
            (r'\bblacklist\b', "blocklist"),
            (r'\bwalkthroughs?\b', "guide/overview"),
            (r'every step of the way', "all along the way"),
            (r'first[- ]class citizen', "top-level / core primitive"),
            (r'drink the kool[- ]aid', "fully commit"),
            (r'tipping point', "turning point / critical threshold"),
            (r'no can do', "cannot do this"),
            (r'grandfathered', "legacy"),
        ]:
            for m in re.finditer(target, full_slide_text, re.IGNORECASE):
                print(f"[SLIDE TEXT VIOLATION] Slide {i}: Found '{m.group(0)}' in slide text! (Should use '{repl}') Context: ...{full_slide_text[max(0, m.start()-30):min(len(full_slide_text), m.end()+30)]}...")
            for m in re.finditer(target, notes, re.IGNORECASE):
                print(f"[NOTES VIOLATION] Slide {i}: Found '{m.group(0)}' in speaker notes! (Should use '{repl}') Context: ...{notes[max(0, m.start()-30):min(len(notes), m.end()+30)]}...")
                
        # Check dashes: em-dash or double-dash
        for m in re.finditer(r'—|--', full_slide_text):
            print(f"[SLIDE DASH VIOLATION] Slide {i}: Found '{m.group(0)}' in slide text (use en dash with spaces ' – ')")
        for m in re.finditer(r'—|--', notes):
            print(f"[NOTES DASH VIOLATION] Slide {i}: Found '{m.group(0)}' in speaker notes (use en dash with spaces ' – ')")
            
        # Check for non-serial commas (A, B and C without comma before and)
        # Regex to find: word, word and word (where no comma before and)
        for m in re.finditer(r'\b([A-Za-z0-9_-]+),\s+([A-Za-z0-9_-]+)\s+and\s+([A-Za-z0-9_-]+)\b', full_slide_text):
            print(f"[SLIDE OXFORD COMMA VIOLATION] Slide {i}: Missing Oxford comma: '{m.group(0)}'")
        for m in re.finditer(r'\b([A-Za-z0-9_-]+),\s+([A-Za-z0-9_-]+)\s+and\s+([A-Za-z0-9_-]+)\b', notes):
            print(f"[NOTES OXFORD COMMA VIOLATION] Slide {i}: Missing Oxford comma: '{m.group(0)}'")

if __name__ == "__main__":
    main()
