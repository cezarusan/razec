"""
Script principal — baixa arquivos, coleta dados e abre o dashboard.
Chamado pelo atalho Devolutiva Pisciculturas.bat
"""
import urllib.request
import os
import sys
import glob
import subprocess
import json
import shutil

URL = "https://raw.githubusercontent.com/cezarusan/razec/claude/pisciculturas-dashboard-devolutiva-kfazaq"

def achar_pasta():
    for p in [r"P:\FOODS\PCP\31 - Originacao", r"P:\FOODS\PCP\31 - Originação"]:
        if os.path.isdir(p):
            return p
    for p in glob.glob(r"P:\FOODS\PCP\31*"):
        if os.path.isdir(p):
            return p
    return None

def baixar(url, destino):
    import time
    print(f"   baixando {os.path.basename(destino)}...", end=" ")
    url_cb = url + f"?t={int(time.time())}"
    req = urllib.request.Request(url_cb, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    with urllib.request.urlopen(req) as resp, open(destino, "wb") as f:
        f.write(resp.read())
    print("OK")

def main():
    print()
    print("=" * 52)
    print("  BTJ Foods — Devolutiva Pisciculturas")
    print("=" * 52)

    # Acha pasta na rede
    pasta = achar_pasta()
    if not pasta:
        input("\nERRO: Pasta P:\\FOODS\\PCP\\31 - Originacao nao encontrada.\nVerifique a conexao com a rede e pressione Enter...")
        sys.exit(1)

    scripts = os.path.join(pasta, "scripts")
    os.makedirs(scripts, exist_ok=True)

    coletar    = os.path.join(scripts, "coletar_devolutiva.py")
    preparar   = os.path.join(scripts, "preparar_dashboard.py")
    html_base  = os.path.join(pasta,   "devolutiva-pisciculturas.html")
    json_path  = os.path.join(pasta,   "devolutiva_dados.json")
    html_final = os.path.join(pasta,   "devolutiva_dashboard_atual.html")

    # 0. Sincroniza arquivo de Biomassa Previsto da pasta Qualidade → Originacao
    BM_ORIGEM  = r"P:\FOODS\QUALIDADE\35 - Indicadores da Qualidade\Indicadores - Doc. recepção pescado.xlsx"
    BM_DESTINO = os.path.join(pasta, "Indicadores - Doc. recepção pescado.xlsx")
    print("\n[0/3] Sincronizando Biomassa Previsto...")
    try:
        if os.path.exists(BM_ORIGEM):
            shutil.copy2(BM_ORIGEM, BM_DESTINO)
            print(f"   OK — arquivo copiado da pasta Qualidade")
        elif os.path.exists(BM_DESTINO):
            print(f"   Pasta Qualidade sem acesso — usando copia local existente")
        else:
            print(f"   AVISO — arquivo nao encontrado em nenhuma das pastas")
    except Exception as e:
        print(f"   Aviso: nao foi possivel copiar ({e}) — usando copia local se existir")

    # 1. Baixa arquivos atualizados
    print("\n[1/3] Baixando arquivos atualizados do GitHub...")
    baixar(URL + "/scripts/coletar_devolutiva.py",            coletar)
    baixar(URL + "/scripts/preparar_dashboard.py",            preparar)
    baixar(URL + "/dashboards/devolutiva-pisciculturas.html", html_base)

    # 2. Coleta dados e gera JSON
    print("\n[2/3] Coletando os 100 ultimos apontamentos...")
    print()
    ret = subprocess.run([sys.executable, coletar, "--simulacao", "--exportar-json"])
    if ret.returncode != 0:
        input("\nERRO ao coletar dados. Pressione Enter para sair...")
        sys.exit(1)

    # 3. Injeta dados no HTML e abre no navegador
    print("\n[3/3] Preparando dashboard...")
    if not os.path.exists(json_path):
        input(f"\nERRO: JSON nao gerado em {json_path}\nPressione Enter para sair...")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        payload = json.load(f)

    registros = payload.get("registros", [])
    gerado_em = payload.get("gerado_em", "")
    total     = len(registros)

    with open(html_base, encoding="utf-8") as f:
        html = f.read()

    info_str = f"{total} abates · gerado em {gerado_em.replace('T', ' ')}"
    dados_js = json.dumps(registros, ensure_ascii=False)

    injecao = (
        f"let BASE = {dados_js};\n"
        f"(function(){{\n"
        f"  document.addEventListener('DOMContentLoaded', function(){{\n"
        f"    var b=document.getElementById('load-banner');\n"
        f"    var i=document.getElementById('banner-info');\n"
        f"    if(b&&i){{ i.textContent='{info_str}'; b.classList.add('visible'); }}\n"
        f"    var s=document.getElementById('sb-fonte');\n"
        f"    if(s) s.textContent='Fonte: devolutiva_dados.json — {total} registros';\n"
        f"  }});\n"
        f"}})();"
    )

    if "let BASE = [...DEMO];" in html:
        html = html.replace("let BASE = [...DEMO];", injecao)
        print(f"   {total} registros injetados no dashboard")
    else:
        print("   AVISO: marcador nao encontrado, abrindo dashboard sem dados injetados")

    with open(html_final, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n   Abrindo: {html_final}")
    os.startfile(html_final)

    print()
    print("=" * 52)
    print("  Dashboard aberto com sucesso!")
    print("=" * 52)
    print()
    input("Pressione Enter para fechar...")

if __name__ == "__main__":
    main()
