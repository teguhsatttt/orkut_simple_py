
import json
from urllib.parse import urljoin
import httpx

def _dig(obj, path: str):
    cur = obj
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur

class OrkutProvider:
    def __init__(self, cfg: dict):
        pv = cfg["provider"]
        self.base = pv["base_url"].rstrip("/") + "/"
        self.paths = pv["paths"]
        self.http_method = { "create": pv.get("http_method",{}).get("create","GET").upper(),
                             "status": pv.get("http_method",{}).get("status","GET").upper() }
        self.merchant = pv.get("merchant")
        self.codeqr = pv.get("codeqr")
        self.auth = pv.get("auth", {"mode":"none"})
        self.key_param = pv.get("key_param","keyorkut")
        self.key_candidates = pv.get("key_candidates", ["keyorkut","order_id"])
        self.qr_candidates = pv.get("qr_candidates", ["qrcode","qr"])
        self.success_markers = [s.lower() for s in pv.get("success_markers", ["paid","success"])]
        self.client = httpx.Client(timeout=20)

    def _url(self, path: str) -> str:
        return urljoin(self.base, path.lstrip("/"))

    def create_payment(self, amount: int, note: str = "") -> dict:
        url = self._url(self.paths["create"])
        params = {"amount": amount}
        if self.codeqr: params["codeqr"] = self.codeqr

        mode = self.auth.get("mode","none")
        if self.http_method["create"] == "GET":
            if mode == "basic":
                r = self.client.get(url, params=params, auth=(self.auth.get("username"), self.auth.get("password")))
            elif mode == "body":
                params.update({"auth_username": self.auth.get("username"), "auth_token": self.auth.get("password")})
                r = self.client.get(url, params=params)
            else:
                r = self.client.get(url, params=params)
        else:
            body = {"amount": amount, "note": note}
            if mode == "body":
                body.update({"auth_username": self.auth.get("username"), "auth_token": self.auth.get("password")})
            if mode == "basic":
                r = self.client.post(url, json=body, auth=(self.auth.get("username"), self.auth.get("password")))
            else:
                r = self.client.post(url, json=body)
        r.raise_for_status()
        return r.json()

    def extract_key_and_qr(self, resp: dict):
        key = None
        for k in self.key_candidates:
            v = _dig(resp, k) if "." in k else resp.get(k)
            if v: key = v; break
        qr = None
        for k in self.qr_candidates:
            v = _dig(resp, k) if "." in k else resp.get(k)
            if v: qr = v; break
        return key, qr

    def cek_status(self, key_value: str) -> dict:
        url = self._url(self.paths["status"])
        params = { self.key_param: key_value }
        if self.merchant: params["merchant"] = self.merchant

        mode = self.auth.get("mode","none")
        if self.http_method["status"] == "GET":
            if mode == "basic":
                r = self.client.get(url, params=params, auth=(self.auth.get("username"), self.auth.get("password")))
            elif mode == "body":
                params.update({"auth_username": self.auth.get("username"), "auth_token": self.auth.get("password")})
                r = self.client.get(url, params=params)
            else:
                r = self.client.get(url, params=params)
        else:
            body = dict(params)
            if mode == "body":
                body.update({"auth_username": self.auth.get("username"), "auth_token": self.auth.get("password")})
            if mode == "basic":
                r = self.client.post(url, json=body, auth=(self.auth.get("username"), self.auth.get("password")))
            else:
                r = self.client.post(url, json=body)
        r.raise_for_status()
        return r.json()

    def is_paid(self, status_resp: dict) -> bool:
        s = json.dumps(status_resp, ensure_ascii=False).lower()
        return any(mark in s for mark in self.success_markers)
