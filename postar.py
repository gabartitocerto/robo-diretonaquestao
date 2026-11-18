"""
Robô de postagem automática com Trava de Aprovação do Admin — @diretonaquestao / @gabaritocerto2026
Publica no Instagram (API Oficial — Graph API v23.0) os posts e Reels de Plantão aprovados da fila.json.

Modos (variável MODO):
  postar  -> publica o post/Reels APROVADO pelo Admin mais antigo cuja data + hora já chegaram (padrão)
  forcar  -> publica o próximo post APROVADO (ou o POST_ID informado pelo Admin), ignorando a data/hora
  testar  -> só confere o token e se as mídias estão acessíveis (não publica nada)

Regras extras da fila (todas opcionais):
  "expira_em": "AAAA-MM-DD HH:MM" no post -> depois desse momento a notícia NÃO é mais publicada
                (ex.: fim das inscrições). O post fica com status "vencido".
  "intervalo_minimo_min" na fila -> minutos mínimos entre duas publicações (padrão 120),
                para o robô nunca soltar vários posts em sequência.

Variáveis de ambiente:
  IG_TOKEN  (obrigatória) token de acesso do Instagram — fica no GitHub Secrets
  BASE_URL  (opcional) endereço público das imagens/vídeos; padrão = GitHub Pages do repositório
  POST_ID   (opcional) ID específico de um post disparado manualmente pelo Admin (ex.: P01 ou N01)
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

# Token de Login Unificado/Facebook (começa com "EAA") usa graph.facebook.com;
# token de "Login do Instagram" (começa com "IG") usa graph.instagram.com.
_TK = os.environ.get("IG_TOKEN", "").strip()
API = "https://graph.facebook.com/v23.0" if _TK.startswith("EAA") else "https://graph.instagram.com/v23.0"
IG_USER_ID = os.environ.get("IG_USER_ID", "17841458824570192").strip()  # id público da conta @diretonaquestao
FILA = "fila.json"
FUSO = ZoneInfo("America/Sao_Paulo")

TOKEN = os.environ.get("IG_TOKEN", "").strip()
MODO = os.environ.get("MODO", "postar").strip().lower() or "postar"
POST_ID = os.environ.get("POST_ID", "").strip().upper()


def base_url():
    url = os.environ.get("BASE_URL", "").strip()
    if not url:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if "/" not in repo:
            sys.exit("ERRO: defina BASE_URL ou rode dentro do GitHub Actions.")
        dono, nome = repo.split("/", 1)
        url = f"https://{dono.lower()}.github.io/{nome}/"
    return url if url.endswith("/") else url + "/"


def resolver_url_midia(caminho, base):
    if caminho.startswith("http://") or caminho.startswith("https://"):
        return caminho
    return base + caminho.lstrip("/")


def chamar(metodo, caminho, **params):
    params["access_token"] = TOKEN
    dados = urllib.parse.urlencode(params)
    url = f"{API}/{caminho}"
    if metodo == "GET":
        req = urllib.request.Request(f"{url}?{dados}")
    else:
        req = urllib.request.Request(url, data=dados.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="replace")
        sys.exit(f"ERRO da API do Instagram ({e.code}) em {caminho}: {corpo}")


def conferir_imagem(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            tipo = r.headers.get("Content-Type", "").lower()
            if "image/jpeg" not in tipo and "image/jpg" not in tipo:
                sys.exit(f"ERRO: {url} precisa ser JPEG para a API do Instagram (Content-Type: {tipo})")
    except urllib.error.HTTPError as e:
        sys.exit(
            f"ERRO: imagem não encontrada ({e.code}): {url}\n"
            "Confira se o GitHub Pages está ativado e já terminou de publicar."
        )


def esperar_container(cid, tentativas=50):
    for _ in range(tentativas):
        st = chamar("GET", cid, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"ERRO: o Instagram recusou a mídia {cid} (status {st}).")
        time.sleep(5)
    sys.exit(f"ERRO: tempo esgotado esperando a mídia {cid} ficar pronta.")


def obter_legenda(post):
    texto = (post.get("legenda_texto") or "").strip()
    if texto:
        return texto
    caminho = post.get("legenda", "")
    if caminho and os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def url_existe_jpeg(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return "image/jp" in r.headers.get("Content-Type", "").lower()
    except Exception:
        return False


def publicar_story(ig_id, post, base):
    """Publica o story com a arte no formato 9:16 (posts/<ID>/story.jpg).
    A arte do feed (4:5) NÃO serve para story: o Instagram dá zoom e corta as laterais.
    Se o story.jpg não existir, o story é pulado (melhor sem story do que com a arte cortada)."""
    rel = (post.get("story") or "").strip()
    if not rel and post.get("slides"):
        rel = post["slides"][0].rsplit("/", 1)[0] + "/story.jpg"
    url = resolver_url_midia(rel, base) if rel else ""
    if not url or not url_existe_jpeg(url):
        print(f"Aviso: story pulado, não achei a arte 9:16 em {rel or '(sem caminho)'}. Rode gerar_story.py.")
        return
    try:
        story_cid = chamar("POST", f"{ig_id}/media", media_type="STORIES", image_url=url)["id"]
        esperar_container(story_cid, tentativas=25)
        chamar("POST", f"{ig_id}/media_publish", creation_id=story_cid)
        print("Story publicado no formato 9:16 (sem corte).")
    except SystemExit as e:  # o story nunca pode derrubar a publicação principal
        print(f"Aviso: story não enviado ({e})")


def publicar(ig_id, post, base):
    legenda = obter_legenda(post)

    # Suporte nativo a Reels (vídeo MP4 público) na Graph API v23.0
    video_rel = (post.get("video_url") or "").strip()
    if not video_rel and post.get("slides"):
        primeiro = post["slides"][0]
        if primeiro.lower().endswith(".mp4"):
            video_rel = primeiro

    if video_rel:
        v_url = resolver_url_midia(video_rel, base)
        params_reel = {
            "media_type": "REELS",
            "video_url": v_url,
            "caption": legenda,
            "share_to_feed": "true",
        }
        if post.get("cover_url"):
            params_reel["cover_url"] = resolver_url_midia(post["cover_url"], base)
        cid = chamar("POST", f"{ig_id}/media", **params_reel)["id"]
        esperar_container(cid, tentativas=60)
        pub = chamar("POST", f"{ig_id}/media_publish", creation_id=cid)["id"]
        publicar_story(ig_id, post, base)
        return pub

    # Publicação de Imagem Única ou Carrossel
    urls = [resolver_url_midia(s, base) for s in post["slides"]]
    for u in urls:
        conferir_imagem(u)

    if len(urls) == 1:
        cid = chamar("POST", f"{ig_id}/media", image_url=urls[0], caption=legenda)["id"]
    else:
        filhos = []
        for u in urls:
            filho = chamar("POST", f"{ig_id}/media", image_url=u, is_carousel_item="true")["id"]
            esperar_container(filho)
            filhos.append(filho)
        cid = chamar(
            "POST",
            f"{ig_id}/media",
            media_type="CAROUSEL",
            children=",".join(filhos),
            caption=legenda,
        )["id"]

    esperar_container(cid)
    pub_id = chamar("POST", f"{ig_id}/media_publish", creation_id=cid)["id"]

    publicar_story(ig_id, post, base)

    return pub_id


def chave_agendamento(post, horario_padrao="19:00"):
    hora = (post.get("hora") or horario_padrao or "19:00").strip()
    if len(hora) == 4 and ":" in hora:
        hora = "0" + hora
    return f"{post['data']} {hora}"


def venceu(post, agora_str):
    """True quando a notícia tem validade (expira_em) e ela já passou."""
    exp = (post.get("expira_em") or "").strip()
    return bool(exp) and exp <= agora_str


def minutos_desde_ultima_publicacao(fila, agora_dt):
    ultimas = []
    for p in fila["posts"]:
        try:
            ultimas.append(datetime.datetime.fromisoformat(p.get("publicado_em") or ""))
        except ValueError:
            pass
    if not ultimas:
        return None
    return (agora_dt - max(ultimas)).total_seconds() / 60


def salvar_fila(fila):
    with open(FILA, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    if not TOKEN:
        sys.exit("ERRO: o segredo IG_TOKEN não foi configurado.")

    if API.startswith("https://graph.facebook.com"):
        eu = chamar("GET", IG_USER_ID, fields="id,username")
        ig_id = eu.get("id") or IG_USER_ID
    else:
        eu = chamar("GET", "me", fields="user_id,username")
        ig_id = eu.get("user_id") or eu.get("id")
    print(f"Conectado como @{eu.get('username')} (id {ig_id})")

    with open(FILA, encoding="utf-8") as f:
        fila = json.load(f)

    base = base_url()
    agora_dt = datetime.datetime.now(FUSO)
    agora_str = agora_dt.strftime("%Y-%m-%d %H:%M")
    horario_padrao = fila.get("horario_padrao", "19:00")
    exigir_admin = fila.get("exigir_aprovacao_admin", True)

    # Notícia com prazo vencido nunca vai ao ar (ex.: "últimos dias" depois do fim das inscrições).
    mudou = False
    if MODO != "testar":
        for p in fila["posts"]:
            if not p.get("publicado_em") and p.get("status") not in ("pausado", "vencido") and venceu(p, agora_str):
                print(f"⌛ VENCIDO: {p['id']} ({p['titulo']}) expirou em {p['expira_em']} e não será publicado.")
                p["status"] = "vencido"
                mudou = True
    if mudou:
        salvar_fila(fila)

    nao_publicados = [
        p for p in fila["posts"]
        if not p.get("publicado_em") and p.get("status") not in ("pausado", "vencido")
    ]
    aprovados = [p for p in nao_publicados if p.get("aprovado") is True]

    print(
        f"Agora (Brasília): {agora_str} | Não publicados: {len(nao_publicados)} | "
        f"Aprovados pelo Admin: {len(aprovados)}"
    )

    if MODO == "testar":
        amostra = aprovados[:3] or nao_publicados[:3]
        for p in amostra:
            for s in p["slides"]:
                if not s.lower().endswith(".mp4"):
                    conferir_imagem(resolver_url_midia(s, base))
        print("TESTE OK: token válido e mídias acessíveis. Nada foi publicado.")
        return

    if MODO == "postar" and not fila.get("auto_post_ativo", True):
        print("Envio automático está PAUSADO nas configurações do Admin. Encerrando.")
        return

    if POST_ID:
        alvo = [p for p in fila["posts"] if p["id"].upper() == POST_ID and not p.get("publicado_em")]
        if not alvo:
            print(f"Post {POST_ID} não encontrado ou já publicado.")
            return
        if exigir_admin and not alvo[0].get("aprovado"):
            sys.exit(f"BLOQUEADO: Post {POST_ID} ainda não foi aprovado pelo Admin.")
        candidatos = alvo
    elif MODO == "forcar":
        candidatos = aprovados if exigir_admin else nao_publicados
    else:
        bloqueados = [
            p for p in nao_publicados
            if not p.get("aprovado") and chave_agendamento(p, horario_padrao) <= agora_str
        ]
        for b in bloqueados:
            print(
                f"⏳ BLOQUEADO PELA TRAVA DO ADMIN: {b['id']} ({b['titulo']}) agendado para "
                f"{chave_agendamento(b, horario_padrao)} ainda NÃO foi aprovado pelo Admin."
            )

        base_lista = aprovados if exigir_admin else nao_publicados
        candidatos = [
            p for p in base_lista
            if chave_agendamento(p, horario_padrao) <= agora_str
        ]

    if len(aprovados) <= 2:
        print(f"⚠️ FILA BAIXA: só {len(aprovados)} post(s) aprovado(s) esperando. Hora de preparar novas notícias.")

    if not candidatos:
        print("Nenhum post aprovado com horário atingido agora. Até a próxima verificação!")
        return

    if MODO == "postar" and not POST_ID:
        intervalo = int(fila.get("intervalo_minimo_min", 120))
        desde = minutos_desde_ultima_publicacao(fila, agora_dt)
        if desde is not None and 0 <= desde < intervalo:
            print(
                f"⏱️ Última publicação há {int(desde)} min. O intervalo mínimo é de {intervalo} min; "
                "o próximo post sai em uma das próximas verificações."
            )
            return

    post = sorted(candidatos, key=lambda p: chave_agendamento(p, horario_padrao))[0]
    print(f"🚀 Publicando {post['id']} — {post['titulo']} (Aprovado por {post.get('aprovado_por') or 'Admin'}) ...")
    media_id = publicar(ig_id, post, base)

    post["status"] = "publicado"
    post["publicado_em"] = agora_dt.isoformat(timespec="seconds")
    post["media_id"] = media_id
    salvar_fila(fila)
    print(f"✅ PUBLICADO COM SUCESSO! {post['id']} (media_id {media_id})")


if __name__ == "__main__":
    main()
