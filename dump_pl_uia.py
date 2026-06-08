"""
Dump Phone Link UIA tree — find the number input / dialer text field.
Run with: python dump_pl_uia.py
"""
import sys
import time
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

import uiautomation as auto

print("Searching for Phone Link window...")
pl = None
for child in auto.GetRootControl().GetChildren():
    name = child.Name or ""
    if "phone link" in name.lower():
        pl = child
        print(f"Found: '{name}' class={child.ClassName} HWND={child.NativeWindowHandle}")
        break

if not pl:
    print("Phone Link NOT found")
    sys.exit(1)

rect = pl.BoundingRectangle
print(f"Window rect: L={rect.left} T={rect.top} R={rect.right} B={rect.bottom}")
print(f"Size: {rect.right-rect.left}x{rect.bottom-rect.top}")
print()

# Dump children 2 levels deep, looking for Edit/Text/TextBox controls
def dump(control, depth=0, max_depth=3):
    prefix = "  " * depth
    name = control.Name or ""
    cls = control.ClassName or ""
    ct = control.ControlTypeName or ""
    rid = control.AutomationId or ""
    cr = control.BoundingRectangle
    
    # Only print interesting controls
    is_interesting = any(k in ct.lower() + cls.lower() + name.lower() 
                         for k in ["edit", "text", "input", "dial", "number", "search", "box", "phone"])
    
    if is_interesting or depth <= 1:
        size_str = f"[{cr.left},{cr.top},{cr.right},{cr.bottom}]"
        print(f"{prefix}{ct} | {cls} | name='{name}' | id='{rid}' | {size_str}")
    
    if depth < max_depth:
        try:
            for child in control.GetChildren():
                dump(child, depth+1, max_depth)
        except:
            pass

print("=== UIA Tree (interesting controls) ===")
dump(pl)
print()
print("=== Done ===")
