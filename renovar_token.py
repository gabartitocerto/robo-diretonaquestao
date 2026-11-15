"""
Renova o token do Instagram (vale 60 dias; renovando toda semana ele nunca expira).
Grava o token novo em $RUNNER_TEMP/novo_token para o workflow atualizar o segredo IG_TOKEN.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ.get("IG_TOKEN", "").strip()
if not token:
    sys.exit("ERRO: IG_TOKEN não configurado.")

url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": token})
try:
    with urllib.request.urlopen(url, timeout=60) as r:
        dados = json.loads(r.read().decode())
except urllib.error.HTTPError as e:
    sys.exit(f"ERRO ao renovar token ({e.code}): {e.read().decode(errors='replace')}")

novo = dados["access_token"]
print(f"::add-mask::{novo}")
dias = int(dados.get("expires_in", 0)) // 86400
print(f"Token renovado. Validade: {dias} dias.")

destino = os.path.join(os.environ.get("RUNNER_TEMP", "."), "novo_token")
with open(destino, "w", encoding="utf-8") as f:
    f.write(novo)
