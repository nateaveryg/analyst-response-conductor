#!/usr/bin/env python3
"""
Automated Verification Suite for Conductor CI/CD Architectural Workflow Diagrams.
Validates:
1. docs/workflow_cloud_run_cicd.jpg (Cloud Run CI/CD delivery pipeline)
2. docs/workflow_agent_engine_cicd.jpg (Vertex AI Agent Engine CI/CD delivery pipeline)

Verification criteria:
- Authentic JPEG format, valid magic bytes, and uncorrupted stream verification
- High resolution (>1280x720)
- 16:9 widescreen aspect ratio
- Authentic dark slate theme (#0B1120) with low background luminance across full perimeter
- Dynamic range, contrast, and standard deviation
- Chromatic accent distribution (Google Cloud and Vertex AI palettes)
- Architectural visual hierarchy: elevated container cards (#111827) and high-contrast foreground
"""
import math
import os
import unittest
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

TARGET_DIAGRAMS = [
    {
        "filename": "workflow_cloud_run_cicd.jpg",
        "description": "Conductor v3 Cloud Run CI/CD Delivery Pipeline Workflow Diagram",
        "min_size_bytes": 100_000,
    },
    {
        "filename": "workflow_agent_engine_cicd.jpg",
        "description": "Vertex AI Agent Engine CI/CD Delivery Pipeline Workflow Diagram",
        "min_size_bytes": 100_000,
    },
]


class TestWorkflowDiagramsConformance(unittest.TestCase):
    """Verifies that all required workflow diagrams exist, are valid JPEGs, and meet styling specs."""

    def test_01_diagram_files_exist_and_non_empty(self):
        """Validates that both workflow diagram files exist on disk with valid file size."""
        for target in TARGET_DIAGRAMS:
            filepath = DOCS_DIR / target["filename"]
            self.assertTrue(
                filepath.is_file(),
                f"Required diagram file missing: {filepath}",
            )
            file_size = filepath.stat().st_size
            self.assertGreater(
                file_size,
                target["min_size_bytes"],
                f"Diagram {target['filename']} is too small ({file_size} bytes)",
            )

    def test_02_jpeg_magic_bytes_and_markers(self):
        """Validates that both diagram files begin with JPEG SOI (FF D8 FF), end with EOI (FF D9), and pass structural verification."""
        for target in TARGET_DIAGRAMS:
            filepath = DOCS_DIR / target["filename"]
            with open(filepath, "rb") as f:
                content = f.read()
            soi_header = content[:3]
            eoi_footer = content[-2:]
            self.assertEqual(
                soi_header,
                b"\xff\xd8\xff",
                f"File {target['filename']} does not begin with valid JPEG SOI magic bytes: {soi_header}",
            )
            self.assertEqual(
                eoi_footer,
                b"\xff\xd9",
                f"File {target['filename']} does not end with valid JPEG EOI marker (truncated stream): {eoi_footer}",
            )

            # Structural stream verification via PIL verify()
            with open(filepath, "rb") as f:
                with Image.open(f) as img:
                    try:
                        img.verify()
                    except Exception as e:
                        self.fail(f"JPEG structural verify() failed for {target['filename']}: {e}")

    def test_03_resolution_and_aspect_ratio(self):
        """Validates that both diagrams meet the 16:9 aspect ratio and strict minimum resolution (>1280x720)."""
        for target in TARGET_DIAGRAMS:
            filepath = DOCS_DIR / target["filename"]
            with Image.open(filepath) as img:
                self.assertEqual(img.format, "JPEG", f"Expected JPEG format for {target['filename']}")
                width, height = img.size
                self.assertGreater(
                    width,
                    1280,
                    f"Width {width} must be strictly greater than 1280px for {target['filename']}",
                )
                self.assertGreater(
                    height,
                    720,
                    f"Height {height} must be strictly greater than 720px for {target['filename']}",
                )

                aspect_ratio = width / height
                expected_ratio = 16 / 9
                relative_diff = abs(aspect_ratio - expected_ratio) / expected_ratio
                self.assertLess(
                    relative_diff,
                    0.015,
                    f"Aspect ratio {aspect_ratio:.4f} deviates more than 1.5% from 16:9 for {target['filename']}",
                )

                # Validate RGB color mode (prevent CMYK / Grayscale / Alpha incompatibilities)
                self.assertEqual(
                    img.mode,
                    "RGB",
                    f"Expected RGB color mode for {target['filename']}, got {img.mode}",
                )

                # Force full pixel decoding to guarantee no truncated or corrupt JPEG scans
                try:
                    img.load()
                except Exception as e:
                    self.fail(f"Corrupted or truncated JPEG scan stream in {target['filename']}: {e}")

    def test_04_dark_slate_background_and_luminance(self):
        """Validates that both diagrams feature an authentic dark slate (#0B1120) palette and low luminance across a 16-point perimeter."""
        for target in TARGET_DIAGRAMS:
            filepath = DOCS_DIR / target["filename"]
            with Image.open(filepath) as img:
                width, height = img.size
                # Sample 16 perimeter boundary points (corners, quarter-points, and midpoints)
                perimeter_points = [
                    ("top-left", (2, 2)),
                    ("top-q1", (width // 4, 2)),
                    ("top-mid", (width // 2, 2)),
                    ("top-q3", (3 * width // 4, 2)),
                    ("top-right", (width - 3, 2)),
                    ("bottom-left", (2, height - 3)),
                    ("bottom-q1", (width // 4, height - 3)),
                    ("bottom-mid", (width // 2, height - 3)),
                    ("bottom-q3", (3 * width // 4, height - 3)),
                    ("bottom-right", (width - 3, height - 3)),
                    ("left-mid", (2, height // 2)),
                    ("left-q1", (2, height // 4)),
                    ("left-q3", (2, 3 * height // 4)),
                    ("right-mid", (width - 3, height // 2)),
                    ("right-q1", (width - 3, height // 4)),
                    ("right-q3", (width - 3, 3 * height // 4)),
                ]
                for label, coords in perimeter_points:
                    r, g, b = img.getpixel(coords)[:3]
                    luminance = 0.299 * r + 0.587 * g + 0.114 * b
                    self.assertLess(
                        luminance,
                        35.0,
                        f"Perimeter point '{label}' at {coords} of {target['filename']} luminance {luminance:.1f} is not dark slate (<35.0)",
                    )
                    # Slate / navy palette requires blue to be the dominant channel
                    self.assertGreaterEqual(
                        b,
                        r,
                        f"Perimeter point '{label}' at {coords} of {target['filename']} blue ({b}) must dominate red ({r})",
                    )
                    self.assertGreaterEqual(
                        b,
                        g,
                        f"Perimeter point '{label}' at {coords} of {target['filename']} blue ({b}) must dominate green ({g})",
                    )

                # Confirm overall mean image luminance confirms dark canvas using histogram statistics
                grayscale = img.convert("L")
                hist = grayscale.histogram()
                total_px = sum(hist)
                mean_lum = sum(val * count for val, count in enumerate(hist)) / total_px
                self.assertLess(
                    mean_lum,
                    55.0,
                    f"Overall image mean luminance {mean_lum:.1f} indicates canvas is not dark theme (<55.0)",
                )

    def test_05_image_entropy_and_dynamic_range(self):
        """Validates that both diagrams contain non-trivial graphical schematic content with high-contrast text."""
        for target in TARGET_DIAGRAMS:
            filepath = DOCS_DIR / target["filename"]
            with Image.open(filepath) as img:
                grayscale = img.convert("L")
                hist = grayscale.histogram()
                n = sum(hist)
                mean = sum(val * count for val, count in enumerate(hist)) / n
                variance = sum(((val - mean) ** 2) * count for val, count in enumerate(hist)) / n
                std_dev = math.sqrt(variance)

                # Non-trivial schematic content has standard deviation > 15
                self.assertGreater(
                    std_dev,
                    15.0,
                    f"Image {target['filename']} standard deviation {std_dev:.1f} indicates blank or low-detail canvas",
                )

                # High contrast foreground text/accents must reach luminance > 180
                min_lum = next(val for val, count in enumerate(hist) if count > 0)
                max_lum = next(val for val in reversed(range(256)) if hist[val] > 0)
                self.assertGreater(
                    max_lum,
                    180,
                    f"Image {target['filename']} max luminance {max_lum} lacks high-contrast foreground elements",
                )
                self.assertGreater(
                    max_lum - min_lum,
                    150,
                    f"Image {target['filename']} dynamic range {max_lum - min_lum} is insufficient for presentation",
                )

    def test_06_color_distribution_and_chromatic_accents(self):
        """Validates that both diagrams contain authentic Google Cloud and Vertex AI chromatic accents."""
        for target in TARGET_DIAGRAMS:
            filepath = DOCS_DIR / target["filename"]
            with Image.open(filepath) as img:
                hsv = img.convert("HSV")
                raw_hsv = hsv.tobytes()
                total_pixels = img.width * img.height
                saturated_count = 0
                blue_cyan_count = 0
                green_count = 0
                amber_count = 0

                for i in range(0, len(raw_hsv), 3):
                    h, s, v = raw_hsv[i], raw_hsv[i + 1], raw_hsv[i + 2]
                    if s > 60 and v > 60:
                        saturated_count += 1
                        if 115 <= h <= 185:
                            blue_cyan_count += 1
                        elif 60 <= h < 115:
                            green_count += 1
                        elif 20 <= h < 60:
                            amber_count += 1

                accent_pct = (saturated_count / total_pixels) * 100
                self.assertGreater(
                    accent_pct,
                    3.0,
                    f"Image {target['filename']} chromatic accent density {accent_pct:.2f}% is too low (<3.0%)",
                )

                if "cloud_run" in target["filename"]:
                    # Cloud Run CI/CD requires Google Cloud color accents (blue, cyan, green, amber)
                    self.assertGreater(
                        blue_cyan_count,
                        10000,
                        f"Cloud Run diagram lacks required blue/cyan accents ({blue_cyan_count})",
                    )
                    self.assertGreater(
                        green_count,
                        1000,
                        f"Cloud Run diagram lacks required green accents ({green_count})",
                    )
                    self.assertGreater(
                        amber_count,
                        1000,
                        f"Cloud Run diagram lacks required amber accents ({amber_count})",
                    )
                elif "agent_engine" in target["filename"]:
                    # Agent Engine CI/CD requires distinct Vertex AI branding accents (blue/cyan)
                    self.assertGreater(
                        blue_cyan_count,
                        10000,
                        f"Agent Engine diagram lacks required Vertex AI blue/cyan accents ({blue_cyan_count})",
                    )

    def test_07_elevated_container_cards_hierarchy(self):
        """Validates the architectural visual hierarchy: elevated container cards (#111827) and high-contrast foreground."""
        for target in TARGET_DIAGRAMS:
            filepath = DOCS_DIR / target["filename"]
            with Image.open(filepath) as img:
                rgb = img.convert("RGB")
                raw_rgb = rgb.tobytes()
                total_pixels = img.width * img.height
                card_pixels = 0
                fg_pixels = 0

                for i in range(0, len(raw_rgb), 3):
                    r, g, b = raw_rgb[i], raw_rgb[i + 1], raw_rgb[i + 2]
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    if 18.0 <= lum <= 48.0 and b >= r and b >= g:
                        card_pixels += 1
                    elif lum > 150.0:
                        fg_pixels += 1

                card_pct = (card_pixels / total_pixels) * 100
                fg_pct = (fg_pixels / total_pixels) * 100

                # Elevated container cards (#111827) must occupy >50% of the schematic layout
                self.assertGreater(
                    card_pct,
                    50.0,
                    f"Image {target['filename']} elevated container card density {card_pct:.1f}% is insufficient (<50%)",
                )

                # High-contrast foreground schematic content (labels, badges, connectors) must occupy >2%
                self.assertGreater(
                    fg_pct,
                    2.0,
                    f"Image {target['filename']} high-contrast foreground content {fg_pct:.1f}% is insufficient (<2%)",
                )


if __name__ == "__main__":
    unittest.main()



