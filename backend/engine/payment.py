"""
XorPay payment integration for WeChat Native (scan-to-pay).
API docs: https://xorpay.com/doc/native.html
Sign: MD5(name + pay_type + price + order_id + notify_url + app_secret) lowercase
"""
import hashlib
import json
import os
import requests

_config = None


def _load_config():
    global _config
    if _config is not None:
        return _config

    # Priority 1: Environment variables (Render/cloud deployment)
    pay_id = os.environ.get("XORPAY_PAY_ID") or os.environ.get("XORPAY_AID")
    key = os.environ.get("XORPAY_KEY") or os.environ.get("XORPAY_APP_SECRET")
    notify_url = os.environ.get("XORPAY_NOTIFY_URL")
    if pay_id and key and notify_url:
        _config = {
            "pay_id": pay_id,
            "key": key,
            "notify_url": notify_url,
        }
        return _config

    # Priority 2: Config file (local development)
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "xorpay.json",
    )
    if os.path.exists(config_path):
        with open(config_path) as f:
            _config = json.load(f)
        required = ["pay_id", "key", "notify_url"]
        for k in required:
            if k not in _config or not _config[k]:
                raise RuntimeError(f"XorPay config missing required field: {k}")
        return _config

    raise RuntimeError(
        "XorPay config not found. Set XORPAY_PAY_ID, XORPAY_KEY, and XORPAY_NOTIFY_URL "
        "environment variables, or create config/xorpay.json locally."
    )


def _sign(name: str, pay_type: str, price: str, order_id: str, notify_url: str) -> str:
    """
    XorPay signature: MD5(name + pay_type + price + order_id + notify_url + app_secret)
    - Values concatenated directly, NO & or = between them
    - Lowercase hex output
    """
    cfg = _load_config()
    raw = name + pay_type + price + order_id + notify_url + cfg["key"]
    return hashlib.md5(raw.encode("utf-8")).hexdigest().lower()


def _verify_notify(data: dict) -> bool:
    """Verify XorPay async notification signature."""
    # Notify params: name, pay_type, price, order_id, aoid, status, notify_url, sign
    # Sign: MD5(name + pay_type + price + order_id + notify_url + app_secret)
    name = data.get("name", "")
    pay_type = data.get("pay_type", "")
    price = data.get("price", "")
    order_id = data.get("order_id", "")
    notify_url = data.get("notify_url", "")
    sign = data.get("sign", "")
    expected = _sign(name, pay_type, price, order_id, notify_url)
    return sign == expected


def create_native_order(
    total_fee: int,
    out_trade_no: str,
    body: str = "八字AI深度解读",
    notify_url: str = None,
) -> dict:
    """
    Create a XorPay Native (scan-to-pay) order.

    Args:
        total_fee: Amount in 分 (e.g. 1990 = 19.90元)
        out_trade_no: Our order ID
        body: Description shown in WeChat payment

    Returns:
        dict with at least:
          - return_code: 1=success
          - payjs_order_id: the platform order ID
          - qrcode: base64 data URI for QR code image
          - code_url: the original payment URL
    """
    import io, base64
    import qrcode as qrcode_lib

    cfg = _load_config()
    aid = cfg["pay_id"]
    price_yuan = f"{total_fee / 100:.2f}"
    pay_type = "native"

    # Use provided notify_url, or fall back to config
    cb_url = notify_url or cfg["notify_url"]

    sign = _sign(body, pay_type, price_yuan, out_trade_no, cb_url)

    params = {
        "pay_type": pay_type,
        "name": body,
        "order_id": out_trade_no,
        "price": price_yuan,
        "notify_url": cb_url,
        "sign": sign,
    }

    pay_url = f"https://xorpay.com/api/pay/{aid}"
    resp = requests.post(pay_url, data=params, timeout=15)
    result = resp.json()

    status = result.get("status")

    if status == "ok":
        info = result.get("info", {})
        code_url = info.get("qr", "")
        aoid = result.get("aoid", "")

        # Generate QR code from the URL
        qrcode_b64 = ""
        if code_url:
            img = qrcode_lib.make(code_url)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qrcode_b64 = "data:image/png;base64," + base64.b64encode(buf.read()).decode()

        return {
            "return_code": 1,
            "return_msg": "ok",
            "payjs_order_id": aoid,
            "out_trade_no": out_trade_no,
            "code_url": code_url,
            "qrcode": qrcode_b64,
        }
    else:
        return {
            "return_code": 0,
            "return_msg": result.get("status", "未知错误"),
            "payjs_order_id": "",
            "out_trade_no": out_trade_no,
            "code_url": "",
            "qrcode": "",
        }


def check_order(platform_order_id: str) -> dict:
    """
    Query XorPay for order payment status.
    Uses GET https://xorpay.com/api/query/{aoid} — no sign required.

    Return values:
      "status": 1 if paid, 0 if not
      "xpay_status": raw XorPay status (payed/success/new/expire/not_exist)
    """
    url = f"https://xorpay.com/api/query/{platform_order_id}"
    resp = requests.get(url, timeout=10)
    result = resp.json()

    status_str = result.get("status", "not_exist")
    # payed = paid but callback pending; success = paid + callback done
    is_paid = status_str in ("payed", "success")

    return {
        "status": 1 if is_paid else 0,
        "xpay_status": status_str,
        "aoid": platform_order_id,
    }
