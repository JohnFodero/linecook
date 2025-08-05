#!/usr/bin/env python3
"""
Test script for LineCook print functionality
"""

from main import print_label_file, check_print_setup, settings
from PIL import Image, ImageDraw
import tempfile
import os
import json

def create_test_image():
    """Create a simple test image for printing"""
    # Create a 4x6 inch test image at 300 DPI
    width, height = 1200, 1800
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw test content
    draw.rectangle([50, 50, width-50, height-50], outline='black', width=5)
    draw.text((100, 100), "LINECOOK PRINT TEST", fill='black')
    draw.text((100, 200), "This is a test label", fill='black')
    draw.text((100, 300), f"Size: {width}x{height} pixels", fill='black')
    draw.text((100, 400), "If you can read this, printing works!", fill='black')
    
    return image

def main():
    print("🖨️  LineCook Print System Test")
    print("=" * 50)
    
    # Check print setup
    print("\n1. Checking print setup...")
    setup = check_print_setup()
    print(json.dumps(setup, indent=2))
    
    # Show current settings
    print(f"\n2. Current Settings:")
    print(f"   Print Enabled: {settings.print_enabled}")
    print(f"   Print Command: {settings.print_command}")
    print(f"   Print Debug: {settings.print_debug}")
    
    if not settings.print_enabled:
        print("❌ Printing is disabled. Enable it in .env with PRINT_ENABLED=true")
        return
    
    # Create test image
    print("\n3. Creating test image...")
    test_image = create_test_image()
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        test_image.save(tmp.name, 'PNG')
        tmp_path = tmp.name
        print(f"   Test image saved to: {tmp_path}")
    
    try:
        # Test printing
        print("\n4. Testing print functionality...")
        success, message = print_label_file(tmp_path)
        
        if success:
            print(f"✅ Print test successful!")
            print(f"   Message: {message}")
        else:
            print(f"❌ Print test failed!")
            print(f"   Error: {message}")
            
        # Show some troubleshooting info
        print("\n5. Troubleshooting Info:")
        print(f"   Available print commands: {setup['available_commands']}")
        print(f"   Detected printers: {len(setup.get('printers', []))}")
        for printer in setup.get('printers', []):
            print(f"     - {printer}")
            
    finally:
        # Clean up
        try:
            os.unlink(tmp_path)
            print(f"\n   Cleaned up temp file: {tmp_path}")
        except:
            pass

if __name__ == "__main__":
    main()