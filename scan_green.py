"""
Find the green Call button in Phone Link by scanning for green pixels.
Phone Link's call button is typically a green circle with a phone icon.
"""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

from PIL import Image
import struct

# Take screenshot via pyautogui
import pyautogui
img = pyautogui.screenshot()
img.save(r"C:\Users\ggg\projects\auto-pickup\test_steps\scan_call.png")

# Phone Link window bounds (from UIA dump)
PL_LEFT, PL_TOP, PL_RIGHT, PL_BOTTOM = 264, 89, 1053, 678

# Crop to Phone Link window
pl_region = img.crop((PL_LEFT, PL_TOP, PL_RIGHT, PL_BOTTOM))
pl_region.save(r"C:\Users\ggg\projects\auto-pickup\test_steps\pl_cropped.png")
print(f"PL region size: {pl_region.size}")

# Scan for green-ish pixels (Call button is green)
# Green in typical WinUI: RGB around (0, 160-200, 80-120) or similar
# Also could be the accent color green
pixels = pl_region.load()
w, h = pl_region.size

green_pixels = []
for y in range(h):
    for x in range(w):
        r, g, b = pixels[x, y][:3]
        # Look for saturated green: G > R*2 and G > B*1.5 and G > 100
        if g > 100 and g > r * 2 and g > b * 1.5:
            green_pixels.append((x, y, r, g, b))

print(f"Found {len(green_pixels)} green pixels in PL region")

if green_pixels:
    # Cluster them — find the densest area (the button)
    # Simple approach: average of all green pixels
    avg_x = sum(p[0] for p in green_pixels) / len(green_pixels)
    avg_y = sum(p[1] for p in green_pixels) / len(green_pixels)
    
    # Find bounding box of green cluster
    min_x = min(p[0] for p in green_pixels)
    max_x = max(p[0] for p in green_pixels)
    min_y = min(p[1] for p in green_pixels)
    max_y = max(p[2] for p in green_pixels)  # y values
    
    # Fix: recalculate y bounds properly  
    min_y = min(p[1] for p in green_pixels)
    max_y = max(p[1] for p in green_pixels)
    
    center_x_screen = int(PL_LEFT + avg_x)
    center_y_screen = int(PL_TOP + avg_y)
    
    print(f"Green cluster: x=[{min_x},{max_x}] y=[{min_y},{max_y}]")
    print(f"Green cluster center (screen coords): ({center_x_screen}, {center_y_screen})")
    print(f"Green cluster center (local coords): ({avg_x:.0f}, {avg_y:.0f})")
    
    # Show some sample colors
    print(f"Sample green pixels: {green_pixels[:10]}")
else:
    print("No green pixels found!")
    
    # Maybe the button isn't visible yet — let's check what IS at the bottom
    # Print last few rows of the image
    print("\nBottom 20 rows of PL region (looking for any content):")
    for y in range(max(h-20, 0), h):
        row_colors = set()
        for x in range(0, w, 50):  # sample every 50px
            r, g, b = pixels[x, y][:3]
            row_colors.add(f"({r},{g},{b})")
        print(f"  y={y}: {row_colors}")
