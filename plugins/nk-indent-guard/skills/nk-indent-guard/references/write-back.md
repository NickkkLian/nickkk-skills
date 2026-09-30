# Writing a data file back with its own indentation

Detect the unit from the file you are about to overwrite, then use it. Never rely on a library default.

Python
```python
import json, re
p = "data/items.json"
src = open(p, encoding="utf-8").read()
m = re.search(r"^( +|\t+)\S", src, re.M)          # first indented line
unit = m.group(1) if m else "  "
obj = json.loads(src)
obj["items"][3]["status"] = "done"
with open(p, "w", encoding="utf-8") as fh:
    json.dump(obj, fh, ensure_ascii=False, indent=unit)   # indent accepts a string since Python 3.2
    fh.write("\n")
```

Node
```js
const fs = require("fs");
const p = "data/items.json";
const src = fs.readFileSync(p, "utf8");
const m = src.match(/^( +|\t+)\S/m);
const unit = m ? m[1] : "  ";
const obj = JSON.parse(src);
obj.items[3].status = "done";
fs.writeFileSync(p, JSON.stringify(obj, null, unit) + "\n");
```

Two more things that inflate diffs and are worth preserving: key order (`json.load` keeps it; do not
sort keys unless the file already is sorted) and the trailing newline.
