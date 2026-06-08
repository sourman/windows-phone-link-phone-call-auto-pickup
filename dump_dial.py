import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto

pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
print(f"Phone Link: {pl.Name}")

# Search for anything with "dial", "keypad", "ButtonCall", "TextBox" in name or autoid
def find_relevant(element, depth=0, max_depth=15):
    if depth > max_depth: return
    name = (element.Name or "").replace('\u200e', '')[:80]
    auto_id = element.AutomationId or ""
    ctrl = element.ControlTypeName
    keywords = ["dial", "keypad", "buttoncall", "textbox", "call", "search", "phone", "number"]
    combined = (name + auto_id).lower()
    if any(k in combined for k in keywords):
        print(f"{'  '*depth}{ctrl} | Name='{name}' | AutoId='{auto_id}'")
    try:
        for child in element.GetChildren():
            find_relevant(child, depth + 1, max_depth)
    except: pass

find_relevant(pl)
