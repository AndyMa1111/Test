"""
XorPay payment integration for WeChat Native (scan-to-pay).
API docs: https://xorpay.com/doc
"""
import hashlib
import json
import os
import requests

# --- Config (loaded from config/xorpay.json) ---
_config = None


def _load_config():
    global _config
    if _config is not None:
        return _config
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "xorpay.json",
    )
    if not os.path.exists(config_path):
        raise RuntimeError(
            f"XorPay config not found at {config_path}. "
            "Please register at https://xorpay.com and create config/xorpay.json"
        )
    with open(config_path) as f:
        _config = json.load(f)
    required = ["pay_id", "key", "notify_url"]
    for k in required:
        if k not in _config or not _config[k]:
            raise RuntimeError(f"XorPay config missing required field: {k}")
    return _config


def _sign(params: dict) -> str:
    """
    XorPay signature algorithm:
    1. Sort params alphabetically by key
    2. Build: key1=value1&key2=value2&key=商户密钥
    3. MD5 hash, uppercase
    """
    cfg = _load_config()
    filtered = {k: v for k, v in params.items() if v != "" and k != "sign"}
    sorted_keys = sorted(filtered.keys())
    sign_str = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)
    sign_str += f"&key={cfg['key']}"
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()


def _verify_notify(data: dict) -> bool:
    """Verify XorPay async notification signature."""
    sign = _sign({k: v for k, v in data.items() if k != "sign"})
    return sign == data.get("sign", "")


def create_native_order(
    total_fee: int,
    out_trade_no: str,
    body: str = "八字AI深度解读",
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
          - qrcode: base64 data URI for QR code image (generated from URL if needed)
          - code_url: the original payment URL
    """
    import io, base64
    import qrcode as qrcode_lib

    cfg = _load_config()
    params = {
        "pay_id": cfg["pay_id"],
        "type": "1",                    # 1 = 微信扫码
        "price": str(total_fee),
        "order_id": out_trade_no,
        "notify_url": cfg["notify_url"],
        "body": body,
    }
    params["sign"] = _sign(params)

    pay_url = f"https://xorpay.com/api/pay/{cfg['pay_id']}"
    resp = requests.post(pay_url, data=params, timeout=15)
    result = resp.json()

    code = result.get("status", -1)
    pay_url_result = result.get("url", "")
    order_id = result.get("order_id", "")

    # Generate QR code from the URL if XorPay didn't return one directly
    qrcode_b64 = ""
    if pay_url_result:
        img = qrcode_lib.make(pay_url_result)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        qrcode_b64 = "data:image/png;base64," + base64.b64encode(buf.read()).decode()

    normalized = {
        "return_code": 1 if code == 0 else 0,
        "return_msg": result.get("msg", ""),
        "payjs_order_id": order_id,
        "out_trade_no": out_trade_no,
        "code_url": pay_url_result,
        "qrcode": qrcode_b64,
    }

    return normalized


def check_order(platform_order_id: str) -> dict:
    """
    Query XorPay for order payment status.
    Returns normalized dict where 'status'=1 means paid.
    """
    cfg = _load_config()
    params = {
        "pay_id": cfg["pay_id"],
        "order_id": platform_order_id,
    }
    params["sign"] = _sign(params)

    resp = requests.post("https://xorpay.com/api/check", data=params, timeout=10)
    result = resp.json()

    # Normalize
    return {
        "status": 1 if result.get("status") == 0 and result.get("pay_result") == 1 else 0,
        "order_id": result.get("order_id", ""),
        "out_trade_no": result.get("out_trade_no", ""),
    }
