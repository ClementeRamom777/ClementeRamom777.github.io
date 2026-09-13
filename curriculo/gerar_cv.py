#!/usr/bin/env python3
"""Gerador dos curriculos em HTML autocontido, prontos para impressao em A4.

Entrada : CV_TI.md e CV_Estagio.md (raiz do projeto)
Saida   : curriculo/cv_ti.html e curriculo/cv_estagio.html

Uso: python curriculo/gerar_cv.py
"""

from __future__ import annotations

import html
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent

ARQUIVOS = [
    ("CV_TI.md", "cv_ti.html", "Curriculo - Ramom Siqueira Clemente da Silva - TI"),
    ("CV_Estagio.md", "cv_estagio.html", "Curriculo - Ramom Siqueira Clemente da Silva - Estagio"),
]

# uma data e o trecho em italico no fim da linha: "... · *dez/2024 - jun/2026*"
RE_DATA = re.compile(r"^(.*?)\s*(?:·\s*)?\*([^*]+)\*\s*$")


# --------------------------------------------------------------------------- parsing


def inline(texto: str) -> str:
    """Escapa HTML e converte **negrito** e *italico*."""
    saida = html.escape(texto, quote=False)
    saida = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", saida)
    saida = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", saida)
    return saida


def paragrafos(linhas: list[str]) -> list[list[str]]:
    """Agrupa linhas em blocos separados por linha em branco, ignorando filetes."""
    blocos: list[list[str]] = []
    atual: list[str] = []
    for bruta in linhas:
        linha = bruta.strip()
        if linha == "---":
            linha = ""
        if linha:
            atual.append(linha)
        elif atual:
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    return blocos


def parse(texto: str) -> dict:
    linhas = texto.split("\n")

    corte = next((i for i, l in enumerate(linhas) if l.strip() == "---"), len(linhas))
    cabecalho = paragrafos(linhas[:corte])

    nome = ""
    cargo = ""
    contato: list[str] = []
    disponibilidade = ""
    soltos: list[list[str]] = []

    for bloco in cabecalho:
        primeira = bloco[0]
        if primeira.startswith("# "):
            nome = primeira[2:].strip()
        elif not cargo and re.fullmatch(r"\*\*.+\*\*", primeira):
            cargo = primeira.strip("*")
        else:
            soltos.append(bloco)

    if soltos:
        contato = soltos[0]
    if len(soltos) > 1:
        disponibilidade = " ".join(soltos[1])

    secoes: list[dict] = []
    atual: dict | None = None
    for bruta in linhas[corte:]:
        if bruta.startswith("## "):
            atual = {"titulo": bruta[3:].strip(), "linhas": []}
            secoes.append(atual)
        elif atual is not None:
            atual["linhas"].append(bruta)

    for secao in secoes:
        secao["blocos"] = [bloco_estruturado(b) for b in paragrafos(secao["linhas"])]

    return {
        "nome": nome,
        "cargo": cargo,
        "contato": contato,
        "disponibilidade": disponibilidade,
        "secoes": secoes,
    }


def bloco_estruturado(linhas: list[str]) -> dict:
    """Converte um bloco cru em {titulo, data, descricoes, itens}."""
    bloco = {"titulo": "", "data": "", "descricoes": [], "itens": [], "texto": ""}

    primeira = linhas[0]
    resto = linhas[1:]

    if primeira.startswith("- "):
        resto = linhas
    else:
        m = RE_DATA.match(primeira)
        if m and primeira.startswith("**"):
            bloco["titulo"] = m.group(1).strip()
            bloco["data"] = m.group(2).strip()
        elif primeira.startswith("**"):
            bloco["titulo"] = primeira
        else:
            bloco["texto"] = primeira

    for linha in resto:
        if linha.startswith("- "):
            bloco["itens"].append(linha[2:].strip())
        else:
            bloco["descricoes"].append(linha)

    return bloco


# --------------------------------------------------------------------------- render


def render_bloco(bloco: dict) -> str:
    partes: list[str] = []

    if bloco["texto"]:
        partes.append(f'<p class="para">{inline(bloco["texto"])}</p>')

    if bloco["titulo"]:
        if bloco["data"]:
            partes.append(
                '<div class="head">'
                f'<div class="head-txt">{inline(bloco["titulo"])}</div>'
                f'<div class="head-data">{inline(bloco["data"])}</div>'
                "</div>"
            )
        else:
            partes.append(f'<p class="linha">{inline(bloco["titulo"])}</p>')

    for descricao in bloco["descricoes"]:
        partes.append(f'<p class="desc">{inline(descricao)}</p>')

    if bloco["itens"]:
        itens = "".join(f"<li>{inline(i)}</li>" for i in bloco["itens"])
        partes.append(f"<ul>{itens}</ul>")

    return f'<div class="bloco">{"".join(partes)}</div>'


def render(doc: dict, titulo_pagina: str) -> str:
    cabecalho = [f'<h1 class="nome">{inline(doc["nome"])}</h1>']
    if doc["cargo"]:
        cabecalho.append(f'<p class="cargo">{inline(doc["cargo"])}</p>')
    for linha in doc["contato"]:
        cabecalho.append(f'<p class="contato">{inline(linha)}</p>')
    if doc["disponibilidade"]:
        cabecalho.append(f'<p class="disp">{inline(doc["disponibilidade"])}</p>')

    corpo: list[str] = []
    for secao in doc["secoes"]:
        blocos = "".join(render_bloco(b) for b in secao["blocos"])
        corpo.append(
            '<section class="secao">'
            f'<h2>{inline(secao["titulo"])}</h2>'
            f"{blocos}"
            "</section>"
        )

    return TEMPLATE.format(
        titulo=html.escape(titulo_pagina),
        css=CSS,
        cabecalho="\n".join(cabecalho),
        corpo="\n".join(corpo),
    )


CSS = """
:root { color-scheme: only light; }

* { margin: 0; padding: 0; box-sizing: border-box; }

@page { size: A4; margin: 14mm; }

html, body {
  background: #fff;
  color: #000;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

body {
  font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial,
               "Liberation Sans", "DejaVu Sans", system-ui, sans-serif;
  font-size: 9.6pt;
  line-height: 1.3;
  text-rendering: optimizeLegibility;
  font-variant-ligatures: none;
}

.folha {
  width: 182mm;          /* A4 (210mm) menos as margens de 14mm */
  margin: 0 auto;
  padding: 14mm 0;
}

/* ---------------------------------------------------------------- cabecalho */

.nome {
  font-size: 19.5pt;
  font-weight: 700;
  letter-spacing: 0.055em;
  text-transform: uppercase;
  text-align: center;
  line-height: 1.12;
}

.cargo {
  font-size: 10.2pt;
  font-weight: 600;
  text-align: center;
  letter-spacing: 0.015em;
  margin-top: 2.5pt;
}

.contato {
  font-size: 8.6pt;
  text-align: center;
  margin-top: 1.6pt;
  line-height: 1.25;
}

.disp {
  font-size: 8pt;
  text-align: center;
  margin-top: 2.4pt;
  line-height: 1.25;
}

/* ------------------------------------------------------------------ secoes */

.secao { margin-top: 8.5pt; }

.secao h2 {
  font-size: 9.8pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  border-bottom: 0.9pt solid #000;
  padding-bottom: 1.6pt;
  margin-bottom: 4pt;
}

.bloco {
  break-inside: avoid;
  page-break-inside: avoid;
  margin-top: 4.5pt;
}

.bloco:first-of-type { margin-top: 0; }

/* linha de cargo/instituicao com a data alinhada a direita */
.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8pt;
}

.head-txt { flex: 1 1 auto; }

.head-data {
  flex: 0 0 auto;
  white-space: nowrap;
  text-align: right;
  font-size: 9pt;
}

.head-data em, .desc em, .linha em, .para em { font-style: normal; }

.linha { line-height: 1.34; }

.desc {
  margin-top: 1pt;
  text-align: justify;
}

.para {
  text-align: justify;
  line-height: 1.33;
}

/* ---------------------------------------------------------------- marcadores */

ul {
  list-style: none;
  margin-top: 1.6pt;
}

li {
  position: relative;
  padding-left: 8.5pt;
  margin-top: 1pt;
  line-height: 1.28;
}

li::before {
  content: "\\2022";
  position: absolute;
  left: 1pt;
  top: 0;
}

li:first-child { margin-top: 0; }

/* --------------------------------------------------------------- impressao */

@media print {
  .folha {
    width: auto;
    margin: 0;
    padding: 0;
  }
  .secao h2 {
    break-after: avoid;
    page-break-after: avoid;
  }
  .head {
    break-after: avoid;
    page-break-after: avoid;
  }
  h1, h2 { break-inside: avoid; page-break-inside: avoid; }
}

@media screen {
  body { background: #eceff1; padding: 8mm 0; }
  .folha {
    background: #fff;
    box-shadow: 0 1px 10px rgba(0, 0, 0, 0.18);
    padding: 14mm;
  }
}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>{css}</style>
</head>
<body>
<main class="folha">
<header>
{cabecalho}
</header>
{corpo}
</main>
</body>
</html>
"""


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    for origem, destino, titulo in ARQUIVOS:
        caminho = RAIZ / origem
        doc = parse(caminho.read_text(encoding="utf-8"))
        (SAIDA / destino).write_text(render(doc, titulo), encoding="utf-8")
        print(f"{origem} -> curriculo/{destino}")


if __name__ == "__main__":
    main()
