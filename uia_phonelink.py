import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto

# Find Phone Link
pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
if not pl.Exists(3):
    print("Phone Link not found")
    sys.exit(1)

print(f"Found: {pl.Name}")
print("=" * 80)

def dump(element, depth=0, max_depth=8):
    if depth > max_depth:
        return
    ctrl_type = element.ControlTypeName
    name = (element.Name or "").replace('\u200e', '')[:100]
    class_name = element.ClassName or ""
    auto_id = element.AutomationId or ""
    indent = "  " * depth
    print(f"{indent}{ctrl_type} | Name='{name}' | AutoId='{auto_id}' | Class='{class_name}'")
    try:
        for child in element.GetChildren():
            dump(child, depth + 1, max_depth)
    except:
        pass

dump(pl)
