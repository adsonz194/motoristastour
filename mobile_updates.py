"""One published Android version, shared by the update screen and API gate."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

POLICY_PATH = Path(__file__).with_name("mobile-update.json")


def update_policy():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    enabled = policy.get("mobileAppEnabled", True)
    if type(enabled) is not bool:
        raise ValueError("mobileAppEnabled deve ser true ou false")
    code = policy.get("versionCode")
    if type(code) is not int or not 0 <= code <= 2_100_000_000:
        raise ValueError("versionCode inválido")
    if code:
        url = urlparse(policy.get("apkUrl", ""))
        if (url.scheme != "https" or url.hostname != "github.com" or url.port not in (None, 443)
                or url.username or url.password or url.query or url.fragment
                or not url.path.startswith("/adsonz194/motoristastourapk/releases/download/")
                or not url.path.endswith(".apk")):
            raise ValueError("Use o APK de uma Release HTTPS do repositório motoristastourapk")
        if not re.fullmatch(r"[a-fA-F0-9]{64}", str(policy.get("sha256", ""))):
            raise ValueError("Informe o SHA-256 do APK publicado")
        if not isinstance(policy.get("versionName"), str) or not policy["versionName"].strip():
            raise ValueError("Informe o nome da versão")
    return {
        "mobileAppEnabled": enabled,
        "maintenanceMessage": str(policy.get("maintenanceMessage") or "O aplicativo Android está temporariamente desativado para atualização. Use o site pelo navegador."),
        "websiteUrl": "https://motoristastour.onrender.com/",
        "versionCode": code,
        "minVersionCode": code,
        "versionName": str(policy.get("versionName", "")),
        "apkUrl": str(policy.get("apkUrl", "")),
        "sha256": str(policy.get("sha256", "")).lower(),
        "message": str(policy.get("message") or "Uma nova versão do Motoristas Tour está disponível. Atualize para continuar."),
    }


def requires_update(policy, supplied_code):
    try:
        installed = int(supplied_code or "0")
    except (ValueError, TypeError):
        installed = 0
    return installed < policy["minVersionCode"]
