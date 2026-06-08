"""Check if ButtonCall supports InvokePattern."""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

from collections import deque
import uiautomation as auto

pl = None
for c in auto.GetRootControl().GetChildren():
    if "phone link" in (c.Name or "").lower():
        pl = c
        break

if not pl:
    print("No PL")
    sys.exit(1)

q = deque([(pl, 0)])
btn = None
while q:
    ctrl, d = q.popleft()
    if ctrl.AutomationId == "ButtonCall":
        btn = ctrl
        break
    if d < 6:
        try:
            for child in ctrl.GetChildren():
                q.append((child, d+1))
        except:
            pass

if not btn:
    print("ButtonCall NOT found via UIA")
    sys.exit(1)

print(f"Found: name='{btn.Name}' type={btn.ControlTypeName} aid={btn.AutomationId}")
r = btn.BoundingRectangle
print(f"Rect: [{r.left},{r.top},{r.right},{r.bottom}]")

# Check InvokePattern
try:
    ip = btn.GetInvokePattern()
    print("✓ InvokePattern SUPPORTED!")
    # Try invoking it
    print("Calling Invoke()...")
    ip.Invoke()
    print("✓ Invoke() succeeded — call should be launching NOW!")
except Exception as e:
    print(f"✗ InvokePattern error: {e}")

# Also check .Click()
print(f"Has .Click(): {hasattr(btn, 'Click')}")
if hasattr(btn, "Click"):
    try:
        print(f"Click method: {btn.Click}")
    except:
        pass
