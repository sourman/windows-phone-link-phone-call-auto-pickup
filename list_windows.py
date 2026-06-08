import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto
roots = auto.GetRootControl()
for c in roots.GetChildren():
    name = (c.Name or "").replace('\u200e', '')[:80]
    cls = c.ClassName or ""
    print(f"{c.ControlTypeName} | Name='{name}' | Class='{cls}'")
