import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto

pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
print(f"Phone Link: {pl.Name}")

# Dump everything with AutoId
def dump(element, depth=0, max_depth=10):
    if depth > max_depth: return
    name = (element.Name or "").replace('\u200e', '')[:80]
    auto_id = element.AutomationId or ""
    ctrl = element.ControlTypeName
    indent = "  " * depth
    # Only show items with useful info
    if name or auto_id or depth < 3:
        print(f"{indent}{ctrl} | Name='{name}' | AutoId='{auto_id}'")
    try:
        for child in element.GetChildren():
            dump(child, depth + 1, max_depth)
    except: pass

dump(pl)
