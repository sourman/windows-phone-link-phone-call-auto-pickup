import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto

# Comet is Chromium-based (Chrome_WidgetWin_1)
# Find all Chromium windows
roots = auto.GetRootControl()
for c in roots.GetChildren():
    cls = c.ClassName or ""
    if cls == "Chrome_WidgetWin_1":
        print(f"Found: {c.Name} | Class={cls}")
        print("=" * 80)
        
        def dump(element, depth=0, max_depth=5):
            if depth > max_depth:
                return
            ctrl_type = element.ControlTypeName
            name = (element.Name or "").replace('\u200e', '')[:80]
            auto_id = element.AutomationId or ""
            indent = "  " * depth
            print(f"{indent}{ctrl_type} | Name='{name}' | AutoId='{auto_id}'")
            try:
                for child in element.GetChildren():
                    dump(child, depth + 1, max_depth)
            except:
                pass
        
        dump(c)
