"""Empirical verification and adversarial challenge for presentation 1EXtNoj3Hp9G2WlBH3dkTaLmc8Jb9cZdpDkH3KpLBg3Q."""

import json
import re
import subprocess
import sys

PRES_ID = "1EXtNoj3Hp9G2WlBH3dkTaLmc8Jb9cZdpDkH3KpLBg3Q"

def run_cmd(cmd):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nStderr: {res.stderr}")
    return res.stdout

def get_slides():
    out = run_cmd(["gslides", "list-slides", PRES_ID, "--json"])
    data = json.loads(out)
    return [slide["objectId"] for slide in data]

def get_notes(slide_id):
    out = run_cmd(["gslides", "get-notes", PRES_ID, "--slide", slide_id])
    return out.strip()

def get_slide_text(slide_id):
    # gslides read provides full text, but we can also get per-slide text
    # Let's inspect get-page or list-elements or read
    out = run_cmd(["gslides", "read", PRES_ID])
    slides_text = {}
    current_slide = None
    for line in out.splitlines():
        m = re.match(r"^--- Slide \d+ \(([^)]+)\) ---", line)
        if m:
            current_slide = m.group(1)
            slides_text[current_slide] = []
        elif current_slide:
            slides_text[current_slide].append(line)
    return {k: "\n".join(v).strip() for k, v in slides_text.items()}

def parse_speaker_notes(notes_text):
    """
    Parses structured speaker notes:
    - Main Takeaway: ...
    - Storylines:
      • ...
    - Anticipated Q&A:
      • Q: ...
      • A: ...
    """
    lines = notes_text.splitlines()
    main_takeaway = None
    storylines = []
    qa_pairs = []
    
    current_section = None
    current_q = None
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Main Takeaway:"):
            current_section = "main_takeaway"
            main_takeaway = stripped[len("Main Takeaway:"):].strip()
        elif stripped.startswith("Storylines:"):
            current_section = "storylines"
        elif stripped.startswith("Anticipated Q&A:"):
            current_section = "qa"
        elif current_section == "storylines":
            if stripped.startswith("•") or stripped.startswith("-") or stripped.startswith("*"):
                storylines.append(stripped.lstrip("•-* ").strip())
        elif current_section == "qa":
            if stripped.startswith("• Q:") or stripped.startswith("Q:"):
                current_q = stripped.lstrip("• ").strip()
            elif stripped.startswith("• A:") or stripped.startswith("A:"):
                if current_q:
                    qa_pairs.append((current_q, stripped.lstrip("• ").strip()))
                    current_q = None
    
    return {
        "raw": notes_text,
        "main_takeaway": main_takeaway,
        "storylines": storylines,
        "qa_pairs": qa_pairs,
    }

def count_words(text):
    # Split on whitespace
    return len(text.split())

def check_single_sentence(text):
    if not text:
        return False, "Empty text"
    # A single sentence should not have sentence terminators (.!?) in the middle
    # ending with a period is expected.
    # Check if there are multiple sentences:
    # Look for . ! ? followed by space and capital letter or end of string
    terminators = list(re.finditer(r'[.!?](?:\s+|$)', text))
    if not terminators:
        return False, "No terminating punctuation"
    # If the only terminator is at the end:
    if len(terminators) == 1 and terminators[0].end() >= len(text):
        return True, "Single sentence"
    # Check if intermediate terminators are abbreviations like e.g., i.e., v3.3.1, etc.
    # Let's see if splitting by sentence gives > 1
    # Simple regex for sentence split:
    clean = re.sub(r'\bv\d+\.\d+(?:\.\d+)?\b', 'version', text) # e.g. v3.3.1
    clean = re.sub(r'\b[A-Za-z]\.[A-Za-z]\b', 'abbr', clean) # e.g. e.g.
    parts = [s.strip() for s in re.split(r'[.!?]\s+(?=[A-Z])', clean) if s.strip()]
    if len(parts) > 1:
        return False, f"Multiple sentences detected: {parts}"
    return True, "Single sentence"

def scan_style_violations(text, context_name=""):
    violations = []
    
    # Forbidden terms
    # "native" (must be "built-in")
    for m in re.finditer(r'\bnative\b', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Forbidden term 'native' found at pos {m.start()}: '...{text[max(0, m.start()-20):min(len(text), m.end()+20)]}...' (use 'built-in')")
    
    # "master" / "slave"
    for m in re.finditer(r'\bmaster\b|\bslave\b', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Forbidden term '{m.group(0)}' found at pos {m.start()} (use 'primary'/'secondary')")

    # "whitelist" / "blacklist"
    for m in re.finditer(r'\bwhite-?list\b|\bblack-?list\b', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Forbidden term '{m.group(0)}' found at pos {m.start()} (use 'allowlist'/'blocklist')")

    # "first-class citizen"
    for m in re.finditer(r'first[- ]class citizen', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Forbidden term '{m.group(0)}' found (use 'top-level' / 'core primitive')")

    # Ableist phrasing
    for m in re.finditer(r'\bwalkthroughs?\b|\bwalk through\b', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Ableist phrasing '{m.group(0)}' found (use 'guide' / 'overview')")

    for m in re.finditer(r'every step of the way', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Ableist phrasing '{m.group(0)}' found (use 'all along the way')")

    for m in re.finditer(r'\[here\]|\bclick here\b', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Non-descriptive hyperlink '{m.group(0)}' found")

    # Idioms with troubled history
    for m in re.finditer(r'drink the kool[- ]aid', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Troubled idiom '{m.group(0)}' found")

    for m in re.finditer(r'tipping point', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Troubled idiom '{m.group(0)}' found (use 'turning point' / 'critical threshold')")

    for m in re.finditer(r'no can do', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Troubled idiom '{m.group(0)}' found")

    for m in re.finditer(r'grandfathered', text, re.IGNORECASE):
        violations.append(f"[{context_name}] Troubled idiom '{m.group(0)}' found (use 'legacy')")

    # Dashes check: em dash without spaces or raw double hyphen
    for m in re.finditer(r'—|--', text):
        violations.append(f"[{context_name}] Improper dash '{m.group(0)}' found (use en dash with spaces ' – ')")

    return violations

def main():
    slide_ids = get_slides()
    print(f"Total slides found: {len(slide_ids)}")
    slide_texts = get_slide_text(PRES_ID)
    
    all_findings = []
    
    for idx, s_id in enumerate(slide_ids, start=1):
        print(f"\n==================== SLIDE {idx} ({s_id}) ====================")
        notes = get_notes(s_id)
        parsed = parse_speaker_notes(notes)
        s_text = slide_texts.get(s_id, "")
        
        print("--- Speaker Notes Raw ---")
        print(notes)
        print("-------------------------")
        
        # 1. Main Takeaway Check
        mt = parsed["main_takeaway"]
        if not mt:
            msg = f"Slide {idx} ({s_id}): Missing 'Main Takeaway' section in speaker notes!"
            print(f"FAIL: {msg}")
            all_findings.append(msg)
        else:
            w_count = count_words(mt)
            is_single, reason = check_single_sentence(mt)
            print(f"Main Takeaway: '{mt}'")
            print(f"Word count: {w_count} (Ceiling <= 20)")
            print(f"Single sentence: {is_single} ({reason})")
            if w_count > 20:
                msg = f"Slide {idx} ({s_id}): Main Takeaway exceeds 20 words ceiling! Count: {w_count}. Text: '{mt}'"
                print(f"FAIL: {msg}")
                all_findings.append(msg)
            if not is_single:
                msg = f"Slide {idx} ({s_id}): Main Takeaway is not a single sentence: {reason}. Text: '{mt}'"
                print(f"FAIL: {msg}")
                all_findings.append(msg)
        
        # 2. Storylines Check
        sl = parsed["storylines"]
        print(f"Storylines count: {len(sl)} (Required: exactly 3)")
        if len(sl) != 3:
            msg = f"Slide {idx} ({s_id}): Storylines count is {len(sl)}, expected exactly 3!"
            print(f"FAIL: {msg}")
            all_findings.append(msg)
        for i, s in enumerate(sl, 1):
            print(f"  Bullet {i}: {s}")
            
        # 3. Anticipated Q&A Check
        qa = parsed["qa_pairs"]
        print(f"Anticipated Q&A count: {len(qa)} pairs (Required: 2-3)")
        if len(qa) < 2 or len(qa) > 3:
            msg = f"Slide {idx} ({s_id}): Anticipated Q&A count is {len(qa)}, expected 2 to 3 pairs!"
            print(f"FAIL: {msg}")
            all_findings.append(msg)
        for i, (q, a) in enumerate(qa, 1):
            print(f"  Q{i}: {q}")
            print(f"  A{i}: {a}")
            
        # 4. Style violations scan
        notes_violations = scan_style_violations(notes, f"Slide {idx} Notes")
        slide_violations = scan_style_violations(s_text, f"Slide {idx} SlideText")
        
        for v in notes_violations + slide_violations:
            print(f"STYLE VIOLATION: {v}")
            all_findings.append(v)
            
    print("\n" + "="*50)
    print(f"TOTAL FINDINGS / VIOLATIONS: {len(all_findings)}")
    for f in all_findings:
        print(f" - {f}")

if __name__ == "__main__":
    main()
