"""
Asset Generator Script
======================
Creates dummy clinical images for testing the visual diagnosis feature.
Run this script once to set up the assets folder structure.
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Define project root and assets directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets" / "images"

# Case-specific image configurations
IMAGE_CONFIGS = [
    {
        "filename": "olp_clinical.jpg",
        "color": (220, 220, 240),
        "text": "Oral Lichen Planus\nWhite Striae",
        "text_color": (60, 60, 120)
    },
    {
        "filename": "perio_clinical.jpg",
        "color": (240, 200, 200),
        "text": "Periodontitis\nBleeding Gums",
        "text_color": (120, 40, 40)
    },
    {
        "filename": "herpes_clinical.jpg",
        "color": (240, 230, 200),
        "text": "Primary Herpes\nVesicles & Ulcers",
        "text_color": (120, 100, 40)
    },
    {
        "filename": "behcet_clinical.jpg",
        "color": (240, 210, 210),
        "text": "Behçet Disease\nOral Ulcers",
        "text_color": (120, 60, 60)
    },
    {
        "filename": "syphilis_clinical.jpg",
        "color": (230, 230, 230),
        "text": "Secondary Syphilis\nMucous Patches",
        "text_color": (80, 80, 80)
    },
    {
        "filename": "desquamative_clinical.jpg",
        "color": (250, 200, 200),
        "text": "Desquamative Gingivitis\nErythema & Peeling",
        "text_color": (140, 40, 40)
    }
]


def create_dummy_image(filename: str, color: tuple, text: str, text_color: tuple):
    """
    Creates a dummy clinical image with colored background and text label.
    
    Args:
        filename: Output filename
        color: RGB tuple for background color
        text: Text to display on image
        text_color: RGB tuple for text color
    """
    # Create image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
        font_small = font
    
    # Draw border
    border_width = 20
    draw.rectangle(
        [(border_width, border_width), (width - border_width, height - border_width)],
        outline=text_color,
        width=8
    )
    
    # Draw text in center
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    
    draw.multiline_text(
        (text_x, text_y),
        text,
        fill=text_color,
        font=font,
        align='center'
    )
    
    # Add watermark
    watermark = "DUMMY IMAGE FOR TESTING"
    watermark_bbox = draw.textbbox((0, 0), watermark, font=font_small)
    watermark_width = watermark_bbox[2] - watermark_bbox[0]
    draw.text(
        ((width - watermark_width) // 2, height - 60),
        watermark,
        fill=(150, 150, 150),
        font=font_small
    )
    
    # Save image
    output_path = ASSETS_DIR / filename
    image.save(output_path, 'JPEG', quality=95)
    print(f"✅ Created: {output_path}")


def setup_assets():
    """
    Main function to set up assets directory and generate dummy images.
    """
    print("=" * 60)
    print("ASSET GENERATOR - Visual Diagnosis Setup")
    print("=" * 60)
    
    # Create assets directory if it doesn't exist
    if not ASSETS_DIR.exists():
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {ASSETS_DIR}")
    else:
        print(f"📁 Directory already exists: {ASSETS_DIR}")
    
    print("\n🖼️  Generating dummy clinical images...")
    print("-" * 60)
    
    # Generate each image
    for config in IMAGE_CONFIGS:
        create_dummy_image(
            filename=config["filename"],
            color=config["color"],
            text=config["text"],
            text_color=config["text_color"]
        )
    
    print("-" * 60)
    print(f"\n✅ SUCCESS: Generated {len(IMAGE_CONFIGS)} clinical images")
    print(f"📂 Location: {ASSETS_DIR}")
    print("\nYou can now run the Streamlit app and test visual findings!")
    print("=" * 60)


if __name__ == "__main__":
    setup_assets()
