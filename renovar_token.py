"""
Cuida do token do Instagram (segredo IG_TOKEN). Roda todo domingo pelo GitHub Actions.

- Token de "Login do Instagram" (começa com "IG"): é renovado aqui (vale 60 dias; renovando
  toda semana ele nunca expira). O token novo vai para $RUNNER_TEMP/novo_token e o workflow
  salva no cofre (Secrets).
- Token do Facebook / Login Unificado (começa com "EAA"): a Meta não deixa renovar esse tipo
  sem o segredo do aplicativo. Então aqui ele é CONFERIDO: se está válido e quantos dias faltam.
  Se faltar pouco (ou se já estiver inválido), o workflow falha de propósito e o GitHub manda
  e-mail ao dono, com tempo de gerar um token novo antes de o robô parar de postar.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

AVISAR_COM_DIAS = 15  # falha (e manda e-mail) quando faltar menos que isso

token = os.environ.get("IG_TOKEN", "").strip()
if not token:
    sys.exit("ERRO: IG_TOKEN não configurado.")


def get(url, **params):
    params["access_token"] = token
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="replace").replace(token, "***")
        raise RuntimeError(f"({e.code}) {corpo}")


def data(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%d/%m/%Y")


def dias_ate(ts):
    agora = datetime.datetime.now(datetime.timezone.utc).timestamp()
    return int((ts - agora) // 86400)


# ---------- Token "IG" (Login do Instagram): renova ----------
if not token.startswith("EAA"):
    try:
        dados = get("https://graph.instagram.com/refresh_access_token", grant_type="ig_refresh_token")
    except RuntimeError as e:
        sys.exit(f"ERRO ao renovar token {e}")
    novo = dados["access_token"]
    print(f"::add-mask::{novo}")
    print(f"Token renovado. Validade: {int(dados.get('expires_in', 0)) // 86400} dias.")
    destino = os.path.join(os.environ.get("RUNNER_TEMP", "."), "novo_token")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(novo)
    sys.exit(0)

# ---------- Token "EAA" (Facebook): confere validade ----------
API = "https://graph.facebook.com/v23.0"
IG_USER_ID = os.environ.get("IG_USER_ID", "17841458824570192").strip()

# 1) O token ainda funciona? (mesma chamada que o robô faz antes de postar)
try:
    eu = get(f"{API}/{IG_USER_ID}", fields="id,username")
except RuntimeError as e:
    sys.exit(f"ERRO: o token do Instagram NÃO está funcionando {e}\n"
             "O robô vai parar de postar. Gere um token novo e troque o segredo IG_TOKEN.")
print(f"Token funcionando: conectado como @{eu.get('username')}.")

# 2) Quando ele vence? (debug_token; se a Meta não deixar ler, só avisa)
try:
    info = get(f"{API}/debug_token", input_token=token).get("data", {})
except RuntimeError as e:
    print(f"::warning::Token funcionando, mas não consegui ler a data de validade {e}")
    sys.exit(0)

if not info.get("is_valid", True):
    sys.exit(f"ERRO: a Meta diz que o token é inválido: {info.get('error', {}).get('message', '')}")

problemas = []
vence = info.get("expires_at") or 0
if vence:
    d = dias_ate(vence)
    print(f"Token ({info.get('type', '?')}) vence em {data(vence)} (faltam {d} dias).")
    if d < AVISAR_COM_DIAS:
        problemas.append(f"o token vence em {data(vence)} (faltam {d} dias)")
else:
    print(f"Token ({info.get('type', '?')}) não tem data de vencimento.")

acesso = info.get("data_access_expires_at") or 0
if acesso:
    d = dias_ate(acesso)
    print(f"Acesso aos dados vale até {data(acesso)} (faltam {d} dias).")
    if d < AVISAR_COM_DIAS:
        problemas.append(f"o acesso aos dados vence em {data(acesso)} (faltam {d} dias)")

if problemas:
    sys.exit("ATENÇÃO: " + "; ".join(problemas) +
             ". Gere um token novo e troque o segredo IG_TOKEN antes disso, senão o robô para de postar.")
print("Tudo certo: nada para renovar agora.")
