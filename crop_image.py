from PIL import Image
import sys
import shutil

try:
    # Use the new highly detailed vibration image
    src = r"C:\Users\work\.gemini\antigravity\brain\3b7e3092-f343-4bd0-98b8-ea1ccf812d03\sidebar_bg_vibration_advanced_1781860888609.png"
    shutil.copy(src, "bg_pattern.png")
    
    img = Image.open('bg_pattern.png').convert('RGB')
    gray = img.convert('L')
    bbox = gray.getbbox()
    
    if bbox:
        img = img.crop(bbox)
        
    # ABSOLUTELY NO DIMMING. Max brightness, max contrast native to the generated image.
    img.save('bg_pattern.png')
    print("Successfully saved RAW highly detailed vibration cropped image with NO DIMMING!")
except Exception as e:
    print(f"Error: {e}")
