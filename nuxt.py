"""Decode Sidearm (Nuxt 3) __NUXT_DATA__ payloads from umterps.com pages."""
import json, re
def load_payload(html):
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))
def resolver(arr):
    cache = {}
    def r(i, depth=0):
        if not isinstance(i, int) or i < 0 or i >= len(arr) or depth > 12:
            return i
        v = arr[i]
        if isinstance(v, dict):
            return {k: r(x, depth+1) for k, x in v.items()}
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in ("ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef", "Set", "Map", "Date", "NuxtError"):
                return r(v[1], depth+1) if len(v) > 1 else None
            return [r(x, depth+1) for x in v]
        return v
    return r
def find_objects(html, required_keys):
    arr = load_payload(html); r = resolver(arr)
    out = []
    for i, v in enumerate(arr):
        if isinstance(v, dict) and all(k in v for k in required_keys):
            out.append(r(i))
    return out
