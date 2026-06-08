import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto

# Find Comet windows
roots = auto.GetRootControl()
for c in roots.GetChildren():
    name = (c.Name or "").replace('\u200e', '')[:60]
    cls = c.ClassName or ""
    if "comet" in name.lower() or "perplexity" in name.lower() or "comet" in cls.lower():
        print(f"FOUND: {c.ControlTypeName} | Name='{name}' | Class='{cls}'")
        
print("\n--- All windows ---")
for c in roots.GetChildren():
    name = (c.Name or "").replace('\u200e', '')[:60]
    cls = c.ClassName or ""
    print(f"  {c.ControlTypeName} | Name='{name}' | Class='{cls}'")
