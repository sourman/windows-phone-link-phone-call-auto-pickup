"""
Dump Phone Link DIALER UIA tree — deep dive into the number input.
"""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

import uiautomation as auto

pl = None
for child in auto.GetRootControl().GetChildren():
    if "phone link" in (child.Name or "").lower():
        pl = child
        break

# Find the Dialer group
dialer = None
def find_dialer(ctrl, depth=0):
    global dialer
    aid = ctrl.AutomationId or ""
    if aid == "DialPaneGrid":
        dialer = ctrl
        return True
    if depth < 5:
        try:
            for c in ctrl.GetChildren():
                if find_dialer(c, depth+1):
                    return True
        except:
            pass
    return False

find_dialer(pl)

if not dialer:
    print("Dialer not found!")
    sys.exit(1)

print(f"Dialer: {dialer.ControlTypeName} | {dialer.ClassName} | id='{dialer.AutomationId}'")
print(f"Rect: [{dialer.BoundingRectangle.left},{dialer.BoundingRectangle.top},{dialer.BoundingRectangle.right},{dialer.BoundingRectangle.bottom}]")
print()

def deep_dump(control, depth=0, max_depth=6):
    prefix = "  " * depth
    name = (control.Name or "")[:60]
    cls = (control.ClassName or "")[:40]
    ct = control.ControlTypeName or ""
    rid = (control.AutomationId or "")[:40]
    cr = control.BoundingRectangle
    
    size_str = f"[{cr.left},{cr.top},{cr.right},{cr.bottom} ({cr.right-cr.left}x{cr.bottom-cr.top})]"
    print(f"{prefix}{ct}")
    print(f"{prefix}  class={cls}  name='{name}'  id='{rid}'")
    print(f"{prefix}  rect={size_str}")
    
    if depth < max_depth:
        try:
            for child in control.GetChildren():
                deep_dump(child, depth+1, max_depth)
        except Exception as e:
            print(f"{prefix}  [ERROR: {e}]")

print("=== Full Dialer Tree ===")
deep_dump(dialer)
