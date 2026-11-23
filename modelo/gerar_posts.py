"""Gerador das artes do @diretonaquestao (modelo claro).

Lê modelo/conteudo.json e grava em posts/<ID>/:
  slide-1.jpg (feed 1080x1350), slide-2.jpg (quando houver), story.jpg (1080x1920),
  slide-1.mp4 (Reels de 9 s, só para notícias) e legenda.txt.

Três tipos de post (campo "modelo"):
  noticia -> ficha de um concurso (selo, órgão, cargo, salário, datas, banca e fonte)
  agenda  -> lista de prazos da semana
  questao -> carrossel: slide 1 com a questão, slide 2 com gabarito comentado

Uso:  python modelo/gerar_posts.py            (todos)
      python modelo/gerar_posts.py N24 Q02    (só os IDs informados)
Precisa de: pip install playwright Pillow ; playwright install chromium ; ffmpeg (para o Reels)
"""
import html
import json
import os
import shutil
import subprocess
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
TRILHA = os.path.join(AQUI, "trilha.m4a")

SELOS = {
    "edital": ("EDITAL PUBLICADO", "#1d4ed8", "#fff"),
    "abertas": ("INSCRIÇÕES ABERTAS", "#15803d", "#fff"),
    "ultimos": ("ÚLTIMOS DIAS", "#dc2626", "#fff"),
    "ultimo_dia": ("ÚLTIMO DIA", "#dc2626", "#fff"),
    "previsto": ("CONCURSO PREVISTO", "#f5b800", "#111827"),
    "resultado": ("RESULTADO", "#7c3aed", "#fff"),
    "agenda": ("AGENDA DA SEMANA", "#0b1020", "#ffd200"),
    "questao": ("QUESTÃO DO DIA", "#0b1020", "#ffd200"),
    "gratis": ("10 QUESTÕES GRÁTIS", "#15803d", "#fff"),
    "blackfriday": ("BLACK FRIDAY", "#0b1020", "#ffd200"),
}
ICO = {
    "cal": '<rect x="3.5" y="5" width="17" height="16" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/><path d="M8 14h2M12 14h2M16 14h.5M8 17.5h2M12 17.5h2"/>',
    "taxa": '<ellipse cx="12" cy="6.5" rx="7" ry="3"/><path d="M5 6.5v5.5c0 1.7 3.1 3 7 3s7-1.3 7-3V6.5"/><path d="M5 12v5.5c0 1.7 3.1 3 7 3s7-1.3 7-3V12"/>',
    "prova": '<rect x="5" y="3.5" width="14" height="17.5" rx="2"/><path d="m8.3 8.6 1.2 1.2 2-2.2M8.3 13.6l1.2 1.2 2-2.2M13.5 9h2.5M13.5 14h2.5M8.5 18h7"/>',
    "vagas": '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><path d="M16 4.8a3.2 3.2 0 0 1 0 6.2M18 14.8c1.8.6 3 2.5 3 5.2"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6v.3"/>',
    "banca": '<path d="M4 20h16M6 20V10M10 20V10M14 20V10M18 20V10M3 10l9-6 9 6z"/>',
}
e = html.escape

BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;font-family:"Poppins","Inter",sans-serif;background:#f7f8fb;color:#0f172a;position:relative;overflow:hidden}
.cant{position:absolute;width:260px;height:260px;background:VAR_COR;opacity:.12;transform:rotate(45deg)}
.c1{right:-150px;top:-150px} .c2{left:-150px;bottom:-150px}
.topo{display:flex;justify-content:space-between;align-items:center;padding:52px 60px 0}
.marca{display:flex;align-items:center;gap:16px}
.dq{width:74px;height:74px;border-radius:50%;background:#0b1020;color:#ffd200;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:28px;letter-spacing:-1px;border:3px solid #ffd200}
.marca b{display:block;font-size:26px;line-height:1.1;font-weight:800;letter-spacing:.5px} .marca span{font-size:17px;color:#475569;font-weight:500}
.reg{font-size:20px;font-weight:700;letter-spacing:2px;border:2.5px solid #0f172a;border-radius:10px;padding:8px 18px}
.selo{margin:40px 60px 0;background:VAR_COR;color:VAR_TX;font-weight:800;font-size:66px;line-height:1;padding:24px 30px;text-align:center;letter-spacing:.5px;border-radius:6px}
.pe{position:absolute;left:60px;right:60px;bottom:44px;display:flex;justify-content:space-between;align-items:flex-end;gap:20px;font-size:23px}
.pe b{font-weight:700} .pe .arroba{font-weight:800;font-size:27px} .pe div:last-child{text-align:right;color:#334155;max-width:600px;line-height:1.25}
"""


def casca(n, corpo, css, subtitulo="Notícias de concursos"):
    selo, cor, tx = SELOS[n["selo"]]
    estilo = (BASE_CSS + css).replace("VAR_COR", cor).replace("VAR_TX", tx)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{estilo}</style></head><body>
<div class="cant c1"></div><div class="cant c2"></div>
<div class="topo"><div class="marca"><div class="dq">DQ</div><div><b>DIRETO NA QUESTÃO</b><span>{e(subtitulo)}</span></div></div><div class="reg">{e(n.get("regiao", "RS"))}</div></div>
{corpo}</body></html>'''


def pag_noticia(n):
    selo, cor, tx = SELOS[n["selo"]]
    linhas = "".join(
        f'<div class="ln"><svg viewBox="0 0 24 24">{ICO[i]}</svg><div><small>{e(r)}</small><b>{e(v)}</b></div></div>'
        for i, r, v in n["linhas"]
    )
    css = f"""
.org{{padding:34px 60px 0}} .org b{{display:block;font-size:44px;font-weight:800;line-height:1.1}} .org span{{font-size:30px;color:#334155;font-weight:500}}
.traco{{width:110px;height:8px;background:{cor};margin:16px 60px 0;border-radius:4px}}
.cargo{{padding:22px 60px 0;font-size:{n.get("tam_cargo", 88)}px;font-weight:800;line-height:1.02;letter-spacing:-1.5px;text-transform:uppercase}}
.sal{{display:flex;align-items:center;gap:22px;padding:20px 60px 0}}
.sal small{{font-size:21px;font-weight:700;line-height:1.15;text-transform:uppercase;letter-spacing:.5px;color:#334155}}
.sal i{{width:4px;height:74px;background:{cor};border-radius:2px}}
.sal b{{font-size:{n.get("tam_salario", 78)}px;font-weight:800;letter-spacing:-2px;line-height:1}}
.faixa{{margin:26px 60px 0;background:#0b1020;color:#ffd200;text-align:center;font-weight:700;font-size:{n.get("tam_faixa", 34)}px;padding:13px;letter-spacing:.5px;border-radius:6px}}
.box{{margin:24px 60px 0;border:3.5px solid {cor};border-radius:22px;background:#fff;padding:6px 30px}}
.ln{{display:flex;align-items:center;gap:26px;padding:15px 0;border-bottom:2.5px solid #e2e8f0}} .ln:last-child{{border:0}}
.ln svg{{width:62px;height:62px;flex:none;fill:none;stroke:{cor};stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}}
.ln small{{display:block;font-size:20px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#475569}}
.ln b{{font-size:{n.get("tam_linha", 38)}px;font-weight:700;line-height:1.12}}
"""
    corpo = f'''<div class="selo">{selo}</div>
<div class="org"><b>{e(n["orgao"])}</b><span>{e(n["local"])}</span></div><div class="traco"></div>
<div class="cargo">{e(n["cargo"])}</div>
<div class="sal"><small>{n["rotulo_salario"]}</small><i></i><b>{e(n["salario"])}</b></div>
<div class="faixa">{e(n["faixa"])}</div>
<div class="box ult">{linhas}</div>
<div class="pe"><div><span class="arroba">@diretonaquestao</span><br>{n.get("pe_esq") or "<b>Banca:</b> " + e(n["banca"])}</div><div>{n.get("pe_dir") or "<b>Fonte:</b> " + e(n["fonte"])}</div></div>'''
    return casca(n, corpo, css)


def pag_agenda(n):
    itens = "".join(
        f'<div class="it"><div class="dt"><b>{e(d)}</b><span>{e(dia)}</span></div>'
        f'<div class="tx"><b>{e(org)}</b><span>{e(det)}</span></div></div>'
        for d, dia, org, det in n["itens"]
    )
    css = """
.tit{padding:28px 60px 0;font-size:60px;font-weight:800;line-height:1.05;letter-spacing:-1px}
.sub{padding:4px 60px 0;font-size:27px;color:#334155;font-weight:500}
.lista{margin:22px 60px 0;display:flex;flex-direction:column;gap:11px}
.it{display:flex;align-items:stretch;background:#fff;border:3px solid #0b1020;border-radius:18px;overflow:hidden}
.dt{flex:none;width:190px;background:#0b1020;color:#ffd200;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:8px 6px}
.dt b{font-size:38px;font-weight:800;line-height:1} .dt span{font-size:17px;font-weight:600;color:#fff;letter-spacing:.5px;margin-top:5px;text-transform:uppercase}
.tx{padding:9px 22px;display:flex;flex-direction:column;justify-content:center}
.tx b{font-size:30px;font-weight:800;line-height:1.1} .tx span{font-size:21px;color:#334155;font-weight:500;margin-top:2px}
"""
    corpo = f'''<div class="selo">{SELOS[n["selo"]][0]}</div>
<div class="tit">{e(n["titulo_arte"])}</div><div class="sub">{e(n["subtitulo"])}</div>
<div class="lista ult">{itens}</div>
<div class="pe"><div><span class="arroba">@diretonaquestao</span><br>{n.get("pe_esq", "<b>Salve</b> para não perder o prazo")}</div><div>{n.get("pe_dir") or "<b>Fonte:</b> " + e(n["fonte"])}</div></div>'''
    return casca(n, corpo, css)


def pag_questao(n, slide):
    letras = "ABCDE"
    q = n["questao"]
    if slide == 1:
        alts = "".join(
            f'<div class="al"><i>{letras[k]}</i><span>{e(a)}</span></div>' for k, a in enumerate(q["alternativas"])
        )
        css = f"""
.chip{{margin:26px 60px 0;display:inline-block;background:#e2e8f0;border-radius:999px;padding:9px 24px;font-size:24px;font-weight:700;color:#0f172a}}
.enun{{padding:22px 60px 0;font-size:{q.get("tam_enunciado", 42)}px;font-weight:700;line-height:1.22}}
.alts{{margin:28px 60px 0;display:flex;flex-direction:column;gap:14px}}
.al{{display:flex;align-items:center;gap:22px;background:#fff;border:3px solid #cbd5e1;border-radius:18px;padding:15px 22px}}
.al i{{flex:none;width:58px;height:58px;border-radius:50%;background:#0b1020;color:#ffd200;font-style:normal;font-weight:800;font-size:30px;display:flex;align-items:center;justify-content:center}}
.al span{{font-size:{q.get("tam_alt", 34)}px;font-weight:600;line-height:1.15}}
"""
        corpo = f'''<div class="selo">{SELOS[n["selo"]][0]}</div>
<div class="chip">{e(q["chip"])}</div>
<div class="enun">{e(q["enunciado"])}</div>
<div class="alts ult">{alts}</div>
<div class="pe"><div><span class="arroba">@diretonaquestao</span><br><b>Comente</b> a sua resposta</div><div><b>Gabarito comentado</b><br>no próximo slide &rarr;</div></div>'''
    else:
        c = q["correta"]
        css = f"""
.gab{{margin:40px 60px 0;background:#15803d;color:#fff;border-radius:22px;padding:30px 36px;display:flex;align-items:center;gap:30px}}
.gab i{{flex:none;width:130px;height:130px;border-radius:50%;background:#fff;color:#15803d;font-style:normal;font-weight:800;font-size:84px;display:flex;align-items:center;justify-content:center}}
.gab small{{display:block;font-size:26px;font-weight:700;letter-spacing:2px}} .gab b{{font-size:{q.get("tam_resposta", 44)}px;font-weight:800;line-height:1.1}}
.h{{padding:34px 60px 0;font-size:24px;font-weight:800;letter-spacing:2px;color:#475569;text-transform:uppercase}}
.exp{{padding:10px 60px 0;font-size:{q.get("tam_explicacao", 36)}px;font-weight:500;line-height:1.3}} .exp b{{font-weight:800}}
.fund{{margin:26px 60px 0;border-left:8px solid #0b1020;padding:6px 0 6px 22px;font-size:26px;color:#334155;font-weight:500}}
.app{{position:absolute;left:60px;right:60px;bottom:140px;background:#0b1020;color:#fff;border-radius:22px;padding:28px 34px}}
.app b{{display:block;color:#ffd200;font-size:40px;font-weight:800;line-height:1.1}} .app span{{font-size:27px;font-weight:500}}
"""
        corpo = f'''<div class="gab"><i>{letras[c]}</i><div><small>GABARITO</small><b>{e(q["alternativas"][c])}</b></div></div>
<div class="h">Por quê?</div><div class="exp">{q["explicacao"]}</div>
<div class="fund ult"><b>Base:</b> {e(q["fundamento"])}</div>
<div class="app"><b>Quer treinar mais?</b><span>Milhares de questões comentadas, de graça, no app. Link na bio.</span></div>
<div class="pe"><div><span class="arroba">@diretonaquestao</span><br><b>Siga</b> para a próxima questão</div><div>Questão inédita, no estilo da banca<br>(não é de prova oficial)</div></div>'''
    return casca(n, corpo, css, "Questões de concursos")


def story(src, dst, W=1080, H=1920):
    a = Image.open(src).convert("RGB")
    y = (H - a.height) // 2
    t = Image.new("RGB", (W, H), a.getpixel((540, 2)))
    t.paste(a.crop((0, 0, W, 1)).resize((W, y)), (0, 0))
    t.paste(a.crop((0, a.height - 1, W, a.height)).resize((W, H - y - a.height)), (0, y + a.height))
    t.paste(a, (0, y))
    t.save(dst, "JPEG", quality=92)


def reels(story_jpg, mp4, seg=9, fps=25):
    """Reels vertical de 9 s a partir da arte 9:16, com aproximação lenta e a trilha do canal."""
    if not shutil.which("ffmpeg"):
        print("   (sem ffmpeg: Reels não gerado)")
        return False
    quadros = seg * fps
    filtro = (
        f"scale=2160:3840,zoompan=z='1+0.035*on/{quadros}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={quadros}:s=1080x1920:fps={fps},format=yuv420p"
    )
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", story_jpg]
    if os.path.exists(TRILHA):
        cmd += ["-i", TRILHA]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-vf", filtro, "-frames:v", str(quadros), "-t", str(seg), "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    return True


def foto(pg, conteudo, destino_jpg):
    pg.set_content(conteudo)
    pg.wait_for_timeout(300)
    med = pg.evaluate(
        "()=>{const u=document.querySelector('.ult').getBoundingClientRect();"
        "const l=document.querySelector('.app')||document.querySelector('.pe');"
        "return [Math.round(u.bottom),Math.round(l.getBoundingClientRect().top),document.body.scrollWidth]}"
    )
    png = destino_jpg[:-4] + ".png"
    pg.screenshot(path=png)
    Image.open(png).convert("RGB").save(destino_jpg, "JPEG", quality=93)
    os.remove(png)
    folga = med[1] - med[0]
    return folga, med[2]


def main():
    so = {a.upper() for a in sys.argv[1:]}
    ns = json.load(open(os.path.join(AQUI, "conteudo.json"), encoding="utf-8"))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for n in ns:
            if so and n["id"].upper() not in so:
                continue
            pasta = os.path.join(RAIZ, "posts", n["id"])
            os.makedirs(pasta, exist_ok=True)
            s1 = os.path.join(pasta, "slide-1.jpg")
            modelo = n.get("modelo", "noticia")
            if modelo == "questao":
                r = [foto(pg, pag_questao(n, 1), s1), foto(pg, pag_questao(n, 2), os.path.join(pasta, "slide-2.jpg"))]
            elif modelo == "agenda":
                r = [foto(pg, pag_agenda(n), s1)]
            else:
                r = [foto(pg, pag_noticia(n), s1)]
            story(s1, os.path.join(pasta, "story.jpg"))
            if modelo != "questao":
                reels(os.path.join(pasta, "story.jpg"), os.path.join(pasta, "slide-1.mp4"))
            with open(os.path.join(pasta, "legenda.txt"), "w", encoding="utf-8") as f:
                f.write(n["legenda"].strip() + "\n")
            aviso = "OK" if all(fl >= 18 for fl, _ in r) else "APERTADO: reduza o texto ou a fonte"
            print(n["id"], modelo, "folga(px):", [fl for fl, _ in r], aviso)
        b.close()


if __name__ == "__main__":
    main()
