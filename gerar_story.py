"""Gera a versão STORY (1080x1920) de cada post, sem cortar nada.
A arte do feed (1080x1350) entra inteira no meio; o fundo é esticado para cima e para baixo.
Uso:  python gerar_story.py            -> cria posts/<ID>/story.jpg para todo post que ainda não tem
      python gerar_story.py N18 N19    -> só esses
Precisa do Pillow:  pip install Pillow
"""
import glob, os, sys
from PIL import Image

W, H = 1080, 1920

def fazer_story(origem, destino):
    art = Image.open(origem).convert("RGB")
    if art.width != W:
        art = art.resize((W, round(art.height * W / art.width)), Image.LANCZOS)
    if art.height >= H:                      # arte mais alta que o story: reduz para caber inteira
        art = art.resize((round(art.width * H / art.height), H), Image.LANCZOS)
    y = (H - art.height) // 2
    x = (W - art.width) // 2
    tela = Image.new("RGB", (W, H), art.getpixel((2, 2)))
    if y > 0:                                # estica a primeira e a última linha da arte: emenda invisível
        tela.paste(art.crop((0, 0, art.width, 1)).resize((W, y)), (0, 0))
        tela.paste(art.crop((0, art.height - 1, art.width, art.height)).resize((W, H - y - art.height)), (0, y + art.height))
    tela.paste(art, (x, y))
    tela.save(destino, "JPEG", quality=92)

if __name__ == "__main__":
    ids = [a.upper() for a in sys.argv[1:]]
    pastas = [os.path.join("posts", i) for i in ids] if ids else sorted(glob.glob(os.path.join("posts", "*")))
    for p in pastas:
        src, dst = os.path.join(p, "slide-1.jpg"), os.path.join(p, "story.jpg")
        if os.path.exists(src) and (ids or not os.path.exists(dst)):
            fazer_story(src, dst); print("story criado:", dst)
