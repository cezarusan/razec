"""
Le devolutiva_dados.json e injeta os dados direto no HTML do dashboard.
Gera devolutiva_dashboard_atual.html e abre no navegador automaticamente.
"""
import json
import os
import sys
import glob
import subprocess

def achar_pasta():
    tentativas = [
        r"P:\FOODS\PCP\31 - Originacao",
        r"P:\FOODS\PCP\31 - Originação",
    ]
    for p in tentativas:
        if os.path.isdir(p):
            return p
    # fallback com glob
    resultados = glob.glob(r"P:\FOODS\PCP\31*")
    for r in resultados:
        if os.path.isdir(r):
            return r
    return None

def main():
    pasta = achar_pasta()
    if not pasta:
        print("ERRO: Pasta P:\\FOODS\\PCP\\31 - Originacao nao encontrada.")
        input("Pressione Enter para sair...")
        sys.exit(1)

    json_path    = os.path.join(pasta, "devolutiva_dados.json")
    html_in      = os.path.join(pasta, "devolutiva-pisciculturas.html")
    html_out     = os.path.join(pasta, "devolutiva_dashboard_atual.html")

    # Le JSON
    if not os.path.exists(json_path):
        print(f"ERRO: JSON nao encontrado em: {json_path}")
        input("Pressione Enter para sair...")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        payload = json.load(f)

    registros = payload.get("registros", payload if isinstance(payload, list) else [])
    gerado_em = payload.get("gerado_em", "")
    total     = len(registros)

    # Le HTML
    if not os.path.exists(html_in):
        print(f"ERRO: HTML nao encontrado em: {html_in}")
        input("Pressione Enter para sair...")
        sys.exit(1)

    with open(html_in, encoding="utf-8") as f:
        html = f.read()

    # Injeta dados substituindo o array BASE
    dados_js = json.dumps(registros, ensure_ascii=False)
    info_str = f"{total} abates · gerado em {gerado_em.replace('T', ' ')}"

    injecao = f"""let BASE = {dados_js};
(function(){{
  document.addEventListener('DOMContentLoaded', function(){{
    var b = document.getElementById('load-banner');
    var i = document.getElementById('banner-info');
    if(b && i){{ i.textContent = '{info_str}'; b.classList.add('visible'); }}
    var sb = document.getElementById('sb-fonte');
    if(sb) sb.textContent = 'Fonte: devolutiva_dados.json — {total} registros';
  }});
}})();"""

    if "let BASE = [...DEMO];" in html:
        html = html.replace("let BASE = [...DEMO];", injecao)
        print(f"OK: {total} registros injetados no dashboard")
    else:
        print("AVISO: nao foi possivel injetar dados — abrindo dashboard padrao")

    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Abrindo: {html_out}")
    os.startfile(html_out)

if __name__ == "__main__":
    main()
