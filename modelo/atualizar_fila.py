"""Coloca na fila.json os posts descritos em modelo/conteudo.json.

- Post novo: entra na fila já no formato que o robô entende.
- Post que já está na fila e ainda NÃO foi publicado: é atualizado.
- Post já publicado: nunca é alterado.

Uso:  python modelo/atualizar_fila.py "Nome de quem aprovou"
Sem o nome, os posts entram como NÃO aprovados (o robô não publica).
"""
import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
FILA = os.path.join(RAIZ, "fila.json")


def main():
    quem = " ".join(sys.argv[1:]).strip()
    agora = datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")
    fila = json.load(open(FILA, encoding="utf-8"))
    por_id = {p["id"]: p for p in fila["posts"]}
    for n in json.load(open(os.path.join(AQUI, "conteudo.json"), encoding="utf-8")):
        pid = n["id"]
        pasta = f"posts/{pid}"
        if not os.path.exists(os.path.join(RAIZ, pasta, "slide-1.jpg")):
            print(pid, "sem arte: rode antes  python modelo/gerar_posts.py", pid)
            continue
        atual = por_id.get(pid)
        if atual and atual.get("publicado_em"):
            print(pid, "já publicado: mantido como está")
            continue
        slides = [f"{pasta}/slide-1.jpg"]
        if os.path.exists(os.path.join(RAIZ, pasta, "slide-2.jpg")):
            slides.append(f"{pasta}/slide-2.jpg")
        post = {
            "id": pid,
            "semana": n.get("semana", ""),
            "materia": n["materia"],
            "tipo": n["tipo"],
            "data": n["data"],
            "hora": n["hora"],
            "titulo": n["titulo"],
            "slides": slides,
            "story": f"{pasta}/story.jpg",
            "legenda": f"{pasta}/legenda.txt",
            "legenda_texto": n["legenda"].strip(),
            "status": "aprovado" if quem else "aguardando aprovação",
            "aprovado": bool(quem),
            "aprovado_em": agora if quem else None,
            "aprovado_por": quem or None,
            "publicado_em": None,
            "media_id": None,
            "fonte_conferida_em": n.get("fonte_conferida_em"),
            "fonte": n.get("fonte_fila", n.get("fonte", "")),
        }
        if n.get("expira_em"):
            post["expira_em"] = n["expira_em"]
        if len(slides) == 1 and os.path.exists(os.path.join(RAIZ, pasta, "slide-1.mp4")):
            post["video_url"] = f"{pasta}/slide-1.mp4"
        if atual:
            atual.clear()
            atual.update(post)
            print(pid, "atualizado na fila")
        else:
            fila["posts"].append(post)
            print(pid, "adicionado à fila")
    with open(FILA, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
