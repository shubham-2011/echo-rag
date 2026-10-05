import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

p = r"C:\Users\shibh\.gemini\antigravity-ide\brain\31779caf-558c-4742-843c-1ad44f397da6\.system_generated\steps\25\content.md"
with open(p, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Let's inspect script 8 or all scripts
scripts = re.findall(r"<script[^>]*>(.*?)</script>", text, re.DOTALL)
print(f"Total scripts: {len(scripts)}")
for idx, s in enumerate(scripts):
    if "enqueue" in s:
        print(f"Enqueue found in script {idx}, length: {len(s)}")
        # Let's see what is inside enqueue
        # window.__reactRouterContext.streamController.enqueue(...)
        # Find JSON string inside enqueue
        m = re.search(r"enqueue\((.*?)\);", s, re.DOTALL)
        if m:
            arg = m.group(1).strip()
            print("Enqueue arg length:", len(arg))
            try:
                # The arg is a JSON-encoded string
                raw_json = json.loads(arg)
                print("raw_json type:", type(raw_json))
                # If raw_json is a string, parse it again
                if isinstance(raw_json, str):
                    inner = json.loads(raw_json)
                    print("inner type:", type(inner), "len:", len(inner))
                    # Let's inspect inner elements
                    with open("scratch/parsed_script_8.json", "w", encoding="utf-8") as out:
                        json.dump(inner, out, indent=2)
                    print("Saved scratch/parsed_script_8.json")
            except Exception as e:
                print("Error parsing enqueue arg:", e)
