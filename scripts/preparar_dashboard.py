"""
Le devolutiva_dados.json e injeta os dados direto no HTML do dashboard.
Gera um arquivo devolutiva_dashboard_atual.html pronto para abrir.
"""
import json
import os
import sys

PASTA   = r"P:\FOODS\PCP\31 - Originacao"
JSON    = os.path.join(PASTA, "devolutiva_dados.json")
HTML_IN = os.path.join(PASTA, "devolutiva-pisciculturas.html")
HTML_OUT= os.path.join(PASTA, "devolutiva_dashboard_atual.html")

def main():
    # Le JSON
    if not os.path.exists(JSON):
        print(f"ERRO: JSON nao encontrado: {JSON}")
        sys.exit(1)
    with open(JSON, encoding="utf-8") as f:
        payload = json.load(f)

    registros = payload.get("registros", payload if isinstance(payload, list) else [])
    gerado_em = payload.get("gerado_em", "")
    total     = payload.get("total", len(registros))

    # Le HTML
    if not os.path.exists(HTML_IN):
        print(f"ERRO: HTML nao encontrado: {HTML_IN}")
        sys.exit(1)
    with open(HTML_IN, encoding="utf-8") as f:
        html = f.read()

    # Injeta dados: substitui a linha "let BASE = [...DEMO];"
    dados_js = json.dumps(registros, ensure_ascii=False)
    info_js  = json.dumps({
        "gerado_em": gerado_em,
        "total":     total,
        "fonte":     JSON,
    }, ensure_ascii=False)

    injecao = f"""let BASE = {dados_js};
let _INFO = {info_js};
// dados injetados automaticamente pelo preparar_dashboard.py
(function(){{
  document.addEventListener('DOMContentLoaded', function(){{
    var b = document.getElementById('load-banner');
    var i = document.getElementById('banner-info');
    if(b && i){{
      i.textContent = _INFO.total + ' abates carregados · gerado em ' + (_INFO.gerado_em||'').replace('T',' ');
      b.classList.add('visible');
    }}
    var sb = document.getElementById('sb-fonte');
    if(sb) sb.textContent = 'Fonte: devolutiva_dados.json — ' + _INFO.total + ' registros';
  }});
}})();"""

    if "let BASE = [...DEMO];" in html:
        html = html.replace("let BASE = [...DEMO];", injecao)
    else:
        print("AVISO: marcador 'let BASE = [...DEMO];' nao encontrado no HTML.")
        print("       O HTML sera aberto sem dados injetados.")

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK: Dashboard gerado com {total} registros")
    print(f"    {HTML_OUT}")
    return HTML_OUT

if __name__ == "__main__":
    out = main()
    print(out)
