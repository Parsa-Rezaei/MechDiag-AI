from PIL import Image, ImageEnhance
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
        
    # Slightly dim it so it sits in the background, but keep contrast high
    enhancer_b = ImageEnhance.Brightness(img)
    img = enhancer_b.enhance(0.75)
    
    enhancer_c = ImageEnhance.Contrast(img)
    img = enhancer_c.enhance(1.2)
    
    img.save('bg_pattern.png')
    print("Successfully saved highly detailed vibration cropped image!")
except Exception as e:
    print(f"Error: {e}")
