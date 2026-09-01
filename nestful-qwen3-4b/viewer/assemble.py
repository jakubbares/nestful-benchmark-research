#!/usr/bin/env python3
"""Stitch the template parts + gzip/base64 payload into one standalone HTML file."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "nestful_explorer.html")

head = open(os.path.join(HERE, "tmpl_head.html")).read()
js = "".join(open(os.path.join(HERE, f)).read() for f in
             ("tmpl_js1.js", "tmpl_js2.js", "tmpl_js3.js", "tmpl_js4.js"))
b64 = open(os.path.join(HERE, "payload.b64")).read().strip()

html = head.replace("__PAYLOAD_B64__", b64) + js + "\n</script>\n</body>\n</html>\n"
open(OUT, "w").write(html)
print(f"{OUT}  ->  {os.path.getsize(OUT)/1e6:.2f} MB")
