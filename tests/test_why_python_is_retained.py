"""Comprehensive verification test suite for Why Python is Retained deliverables."""

import os
import re
import unittest
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_PATH = os.path.join(PROJECT_ROOT, "docs", "why_python_is_retained.md")
IMG_PATH = os.path.join(PROJECT_ROOT, "docs", "why_python_retained_arch.jpg")


class TestWhyPythonIsRetained(unittest.TestCase):
    """Verifies technical accuracy, style compliance, and asset requirements."""

    def setUp(self):
        self.assertTrue(os.path.exists(DOC_PATH), f"Document not found at {DOC_PATH}")
        with open(DOC_PATH, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_markdown_file_exists_and_non_empty(self):
        self.assertGreater(len(self.content), 500, "Markdown document is too short")

    def test_primary_technical_driver(self):
        """R1: Articulate Vertex AI Agent Engine Python-only SDK constraints."""
        self.assertIn("Vertex AI Agent Engine", self.content)
        self.assertIn("Reasoning Engine", self.content)
        self.assertIn("cloudpickle", self.content)
        self.assertIn("Cloud Storage", self.content)
        # Check explicit mention of no Go SDK / Python-only constraint
        self.assertTrue(
            re.search(r"no Go SDK", self.content, re.IGNORECASE),
            "Document must state there is no Go SDK for Reasoning Engine",
        )

    def test_runtime_decoupling_and_isolation(self):
        """R2: Articulate user-path isolation and Cloud Run metrics."""
        self.assertTrue(
            re.search(r"completely absent from the user-facing HTTP request path", self.content, re.IGNORECASE)
            or re.search(r"zero python on user path", self.content, re.IGNORECASE),
            "Must confirm Python is absent from user serving path",
        )
        self.assertIn("Cloud Run", self.content)
        self.assertIn("sub-40ms", self.content)
        self.assertIn("30MB", self.content)
        self.assertIn("microVM", self.content)

    def test_pipeline_mitigations_and_metrics(self):
        """R3: Articulate empirical metrics."""
        self.assertIn("94 seconds", self.content)
        self.assertIn("146MB", self.content)
        self.assertIn("under 3 seconds", self.content)
        self.assertIn("Artifact Registry PyPI caching", self.content)

    def test_structural_tier_comparison_table(self):
        """R6: Tier comparison table present."""
        self.assertIn("| Architectural tier |", self.content)
        self.assertIn("Tier 1: Frontend", self.content)
        self.assertIn("Tier 2: Core API & Gateway", self.content)
        self.assertIn("Tier 3: AI Service", self.content)

    def test_image_reference(self):
        """R6: Embedded diagram reference."""
        self.assertIn("why_python_retained_arch.jpg", self.content)

    def test_future_reevaluation_triggers(self):
        """R6: Concrete future re-evaluation triggers."""
        self.assertIn("Future re-evaluation triggers", self.content)
        self.assertIn("Built-in Go SDK", self.content)
        self.assertIn("Google GenAI Go SDK", self.content)

    def test_style_prohibited_terms(self):
        """R4: Official Google Writing Style prohibited terms."""
        prohibited = [
            (r"\bnative\b", "built-in"),
            (r"\bmaster\b", "primary"),
            (r"\bslave\b", "secondary"),
            (r"\bwhitelist\b", "allowlist"),
            (r"\bblacklist\b", "blocklist"),
            (r"\bwalkthroughs?\b", "guide/overview"),
            (r"every step of the way", "all along the way"),
            (r"first[- ]class citizen", "top-level"),
            (r"drink the kool[- ]aid", "fully commit"),
            (r"tipping point", "critical threshold"),
            (r"no can do", "cannot do this"),
            (r"grandfathered", "legacy"),
            (r"\[here\]", "meaningful link text"),
            (r"\bin the hands of\b", "empowerment phrasing"),
            (r"\bneed a hand\b", "need help/support"),
            (r"\bknow where you stand\b", "check your status"),
            (r"\bwalk the walk\b", "delivers/proves"),
            (r"\bget up and running\b", "get started/onboard"),
            (r"\bpure white\b", "plain white"),
            (r"\bwhite lie\b", "minor inaccuracy"),
            (r"\bblack magic\b", "complex logic"),
            (r"\bblack sheep\b", "outlier"),
            (r"\blong time no see\b", "welcome back"),
        ]
        for pattern, replacement in prohibited:
            matches = list(re.finditer(pattern, self.content, re.IGNORECASE))
            self.assertEqual(
                len(matches),
                0,
                f"Prohibited term '{pattern}' found ({len(matches)} occurrences). Use '{replacement}'.",
            )

    def test_style_required_precise_terms(self):
        """R4: Precise terms check."""
        self.assertIn("Built-in", self.content)
        self.assertIn("Primary", self.content)
        self.assertIn("Secondary", self.content)
        self.assertIn("allowlists", self.content.lower())
        self.assertIn("top-level", self.content.lower())

    def test_style_dashes_in_prose(self):
        """R4: Only en dashes with spaces allowed in prose; no em dashes or double hyphens."""
        prose_lines = [l for l in self.content.split("\n") if not l.strip().startswith("|")]
        prose_text = "\n".join(prose_lines)
        em_dashes = list(re.finditer(r"—|--", prose_text))
        self.assertEqual(
            len(em_dashes),
            0,
            f"Prose contains em-dashes or double-hyphens: {em_dashes}. Use en dash with spaces (' – ').",
        )

    def test_style_sentence_length_under_twenty_words(self):
        """R4: Smart Brevity sentence length limit (<15-20 words)."""
        lines = self.content.split("\n")
        prose_sentences = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("|") or line.startswith("!["):
                continue
            # Strip bullet/number prefix
            clean_line = re.sub(r"^(?:-|\d+\.)\s+", "", line)
            clean_line = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean_line)
            clean_line = re.sub(r"`([^`]+)`", r"\1", clean_line)
            for s in re.split(r"(?<=[.!?])\s+", clean_line):
                if s.strip():
                    prose_sentences.append(s.strip())

        for sentence in prose_sentences:
            word_count = len(sentence.split())
            self.assertLess(
                word_count,
                20,
                f"Sentence exceeds 19 words ({word_count} words): '{sentence}'",
            )

    def test_visual_architecture_overview_section(self):
        """R6: Visual architecture overview tier descriptions present."""
        self.assertIn("### Visual architecture overview", self.content)
        self.assertIn("Tier 1: Frontend", self.content)
        self.assertIn("Tier 2: Core API & Gateway", self.content)
        self.assertIn("Tier 3: AI Service", self.content)
        self.assertIn("Zero Python runs on the user path", self.content)

    def test_style_heading_sentence_case_and_brevity(self):
        """R4: Sentence-style capitalization and brevity for all headings."""
        headings = [l.strip() for l in self.content.split("\n") if l.strip().startswith("#")]
        allowed_proper = {
            "Google", "Cloud", "Conductor", "v3", "Python", "Vertex", "AI",
            "Agent", "Engine", "API", "Gateway", "Model", "Armor", "DLP", "SDK",
            "Go", "HTTP", "HTTP/2", "PyPI", "SLSA", "SBOM", "Cloudpickle",
        }
        for heading in headings:
            clean = re.sub(r"^#+\s*", "", heading)
            words = clean.split()
            self.assertLess(
                len(words),
                15,
                f"Heading exceeds 14 words: '{heading}'",
            )
            # Check sentence-style capitalization: words after first word should be lowercase unless proper noun
            # Skip checking word if it follows a colon (subtitle)
            is_subtitle_start = False
            for i, w in enumerate(words):
                bare_w = re.sub(r"^[^\w]+|[^\w]+$", "", w)
                if not bare_w:
                    continue
                if i == 0 or is_subtitle_start:
                    is_subtitle_start = w.endswith(":")
                    continue
                if w.endswith(":"):
                    is_subtitle_start = True
                else:
                    is_subtitle_start = False

                if bare_w[0].isupper() and bare_w not in allowed_proper:
                    self.fail(
                        f"Heading word '{bare_w}' in '{heading}' violates sentence-style capitalization."
                    )

    def test_style_table_cells_and_oxford_commas(self):
        """R4: Table cell brevity and serial Oxford commas."""
        table_lines = [l.strip() for l in self.content.split("\n") if l.strip().startswith("|")]
        for line in table_lines:
            if "---" in line:
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            for cell in cells:
                clean_cell = re.sub(r"\*\*([^*]+)\*\*", r"\1", cell)
                word_count = len(clean_cell.split())
                self.assertLess(
                    word_count,
                    20,
                    f"Table cell exceeds 19 words ({word_count} words): '{cell}'",
                )

        # Serial Oxford comma verification for lists of 3+ items with conjunctions
        conjunction_patterns = [
            r"([A-Za-z0-9_]+),\s+([A-Za-z0-9_]+)\s+and\s+([A-Za-z0-9_]+)",
            r"([A-Za-z0-9_]+),\s+([A-Za-z0-9_]+)\s+or\s+([A-Za-z0-9_]+)",
        ]
        for pattern in conjunction_patterns:
            matches = list(re.finditer(pattern, self.content))
            self.assertEqual(
                len(matches),
                0,
                f"Missing Oxford comma in: {[m.group(0) for m in matches]}. Required format: 'A, B, and C'.",
            )

    def test_style_no_redundant_repeated_phrases(self):
        """R4: Reject redundant repeated phrases within individual lines/bullets."""
        lines = self.content.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("|") or line.startswith("#"):
                continue
            # Look for 3+ word sequences repeated in the same line
            words = [re.sub(r"^[^\w]+|[^\w]+$", "", w).lower() for w in line.split()]
            words = [w for w in words if w]
            seen_phrases = set()
            for i in range(len(words) - 2):
                phrase = " ".join(words[i:i+3])
                if phrase in seen_phrases:
                    self.fail(f"Repeated redundant 3-word phrase '{phrase}' found in line: '{line}'")
                seen_phrases.add(phrase)

    def test_architectural_diagram_properties(self):
        """R5: High-resolution 16:9 JPEG on dark slate canvas."""
        self.assertTrue(os.path.exists(IMG_PATH), f"Image not found at {IMG_PATH}")

        # Verify SOI / EOI magic bytes
        with open(IMG_PATH, "rb") as f:
            raw_bytes = f.read()
        self.assertGreater(
            len(raw_bytes),
            50000,
            f"Image file size {len(raw_bytes)} bytes is too small (<50KB)",
        )
        self.assertEqual(
            raw_bytes[:3],
            b"\xff\xd8\xff",
            "Image must begin with valid JPEG SOI magic bytes",
        )
        self.assertEqual(
            raw_bytes[-2:],
            b"\xff\xd9",
            "Image must end with valid JPEG EOI marker",
        )

        # Structural stream verification
        with open(IMG_PATH, "rb") as f:
            with Image.open(f) as img:
                img.verify()

        # Dimension and aspect ratio checks
        with Image.open(IMG_PATH) as img:
            self.assertEqual(img.format, "JPEG", "Image format must be JPEG")
            self.assertEqual(img.mode, "RGB", "Image color mode must be RGB")
            w, h = img.size
            self.assertGreater(w, 1280, f"Width {w} must be >1280px")
            self.assertGreater(h, 720, f"Height {h} must be >720px")
            ratio = w / h
            target_ratio = 16 / 9
            self.assertAlmostEqual(
                ratio,
                target_ratio,
                delta=0.05,
                msg=f"Aspect ratio {ratio} is not 16:9 ({target_ratio})",
            )

            # Check 16 perimeter points for authentic dark slate (#0B1120) palette
            perimeter_points = [
                (2, 2), (w // 4, 2), (w // 2, 2), (3 * w // 4, 2), (w - 3, 2),
                (2, h - 3), (w // 4, h - 3), (w // 2, h - 3), (3 * w // 4, h - 3), (w - 3, h - 3),
                (2, h // 2), (2, h // 4), (2, 3 * h // 4),
                (w - 3, h // 2), (w - 3, h // 4), (w - 3, 3 * h // 4),
            ]
            for pt in perimeter_points:
                r, g, b = img.getpixel(pt)[:3]
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                self.assertLess(
                    lum,
                    35.0,
                    f"Perimeter point at {pt} luminance {lum:.1f} is not dark slate (<35.0)",
                )
                self.assertGreaterEqual(
                    b,
                    r,
                    f"Perimeter point at {pt} blue ({b}) must dominate red ({r})",
                )
                self.assertGreaterEqual(
                    b,
                    g,
                    f"Perimeter point at {pt} blue ({b}) must dominate green ({g})",
                )

            # Check overall mean canvas luminance
            gray = img.convert("L")
            hist = gray.histogram()
            total_px = sum(hist)
            mean_lum = sum(val * count for val, count in enumerate(hist)) / total_px
            self.assertLess(mean_lum, 55.0, f"Overall canvas mean luminance {mean_lum:.1f} indicates canvas is not dark")

            # Check dynamic range and high-contrast foreground text/elements
            min_lum = next(v for v, c in enumerate(hist) if c > 0)
            max_lum = next(v for v in reversed(range(256)) if hist[v] > 0)
            self.assertGreater(max_lum, 180, "Image lacks high-contrast foreground elements")
            self.assertGreater(max_lum - min_lum, 150, "Dynamic range is insufficient")

            contrast = (max_lum + 0.05) / (min_lum + 0.05)
            self.assertGreater(contrast, 10.0, "Image contrast ratio is too low")


if __name__ == "__main__":
    unittest.main()
