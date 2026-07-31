"""
Coleta automática de dados para Devolutiva Pisciculturas
Lê rendimentoLote3.xlsx e Descarte-ETP.xlsx e grava em Retorno_Pisciculturas.xlsx

Uso:
    python coletar_devolutiva.py
    python coletar_devolutiva.py --simulacao   (não grava, só mostra o resultado)
    python coletar_devolutiva.py --lote 2805   (processa só um lote específico)
"""

import sys
import os
import argparse
from datetime import datetime

try:
    import pandas as pd
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
except ImportError:
    print("❌ Dependências não encontradas. Execute:")
    print("   pip install pandas openpyxl")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIGURAÇÃO — ajuste aqui se necessário
# ─────────────────────────────────────────────

ARQUIVOS = {
    "rendimento": r"P:\FOODS\CONTROLE DE PRODUÇÃO\Industria\Rendimento_Potencial\rendimentoLote3.xlsx",
    "descarte":   r"P:\FOODS\CONTROLE DE PRODUÇÃO\5 - Descartes\Descarte-ETP.xlsx",
    "retorno":    r"P:\FOODS\PCP\31 - Originação\Retorno_Pisciculturas.xlsx",
}

ABA_DESCARTE = "BaseDeDados"
ABA_DESTINO  = "Executado_Base_Dados"

# Colunas do rendimentoLote3.xlsx (índice 0 = coluna A)
# ATENÇÃO: confirme os nomes exatos das colunas ao rodar --inspecionar
COLS_RENDIMENTO = {
    "lote":         "Lote",          # ajuste para o nome real da coluna
    "data":         "Data",          # ajuste para o nome real da coluna
    "unid_prod":    "Unid. Produtora",  # ajuste para o nome real da coluna
    "bm_prev":      "H",             # col H — Biomassa Previsto
    "bm_real":      "I",             # col I — Biomassa Realizado
    "mort_real":    "L",             # col L — Mortalidade Realizado
    "pm_real":      "O",             # col O — PM Realizado (sangria)
    "rend_real":    "AA",            # col AA — Rend. Pot. Realizado
}

# Valores fixos
REND_PREV      = 47.50   # % fixo
MORT_PREV      = 0.00    # kg fixo
DESC_500G_PERC = 0.0020  # 0,20% da Biomassa Realizada
DESC_BACT_PERC = 0.0010  # 0,10% da Biomassa Realizada
DESC_MOLE_PERC = 0.0010  # 0,10% da Biomassa Realizada

# Filtros de SubCateg no Descarte-ETP
SUBCATEG_500G  = ["PEIXE INTEIRO <0,500"]
SUBCATEG_BACT  = ["BACTÉRIA STREPTOCOCCUS", "BACTÉRIA FRANCISELA", "DESCARTE RESÍDUO (BACTÉRIA)"]
SUBCATEG_MOLE  = ["FILE C/COURO MOLE", "FILE REFILADO MOLE", "FILÉ REFILADO MOLE"]

# ─────────────────────────────────────────────


def col_letra_para_idx(letra: str) -> int:
    """Converte letra(s) de coluna Excel para índice 0-based. Ex: 'A'→0, 'AA'→26"""
    letra = letra.upper()
    idx = 0
    for c in letra:
        idx = idx * 26 + (ord(c) - ord('A') + 1)
    return idx - 1


def ler_rendimento(caminho: str) -> pd.DataFrame:
    print(f"\n📂 Lendo: {caminho}")
    df = pd.read_excel(caminho, sheet_name=0, header=0)
    print(f"   {len(df)} linhas encontradas | colunas: {list(df.columns[:10])}{'...' if len(df.columns)>10 else ''}")
    return df


def ler_descarte(caminho: str, aba: str) -> pd.DataFrame:
    print(f"\n📂 Lendo: {caminho} → aba '{aba}'")
    df = pd.read_excel(caminho, sheet_name=aba, header=0)
    print(f"   {len(df)} linhas encontradas | colunas: {list(df.columns)}")
    return df


def mapear_colunas_rendimento(df: pd.DataFrame) -> dict:
    """
    Tenta encontrar as colunas por nome; se não achar, usa índice posicional.
    Retorna dict com chaves normalizadas.
    """
    cols = list(df.columns)

    def get_col(nome_config: str, idx_fallback: int):
        # Tenta nome exato
        if nome_config in cols:
            return nome_config
        # Tenta por letra de coluna (ex: 'H', 'AA')
        if len(nome_config) <= 2 and nome_config.isalpha():
            pos = col_letra_para_idx(nome_config)
            if pos < len(cols):
                return cols[pos]
        # Busca parcial case-insensitive
        nome_lower = nome_config.lower()
        for c in cols:
            if nome_lower in str(c).lower():
                return c
        # Fallback posicional
        if idx_fallback < len(cols):
            print(f"   ⚠  Coluna '{nome_config}' não encontrada — usando posição {idx_fallback} ('{cols[idx_fallback]}')")
            return cols[idx_fallback]
        return None

    return {
        "lote":      get_col(COLS_RENDIMENTO["lote"],      1),
        "data":      get_col(COLS_RENDIMENTO["data"],      0),
        "unid_prod": get_col(COLS_RENDIMENTO["unid_prod"], 4),
        "bm_prev":   get_col(COLS_RENDIMENTO["bm_prev"],   col_letra_para_idx("H")),
        "bm_real":   get_col(COLS_RENDIMENTO["bm_real"],   col_letra_para_idx("I")),
        "mort_real": get_col(COLS_RENDIMENTO["mort_real"],  col_letra_para_idx("L")),
        "pm_real":   get_col(COLS_RENDIMENTO["pm_real"],   col_letra_para_idx("O")),
        "rend_real": get_col(COLS_RENDIMENTO["rend_real"], col_letra_para_idx("AA")),
    }


def somar_descarte(df_desc: pd.DataFrame, lote, subcategs: list) -> float:
    """Soma PeixeVivoKg para um lote e lista de SubCateg."""
    col_lote = None
    col_subcateg = None
    col_valor = None

    for c in df_desc.columns:
        cl = str(c).lower()
        if "lote" in cl and col_lote is None:
            col_lote = c
        if "subcateg" in cl and col_subcateg is None:
            col_subcateg = c
        if "peixovivo" in cl.replace(" ","") or "peixevivo" in cl.replace(" ","") and col_valor is None:
            col_valor = c

    if not col_lote or not col_subcateg or not col_valor:
        print(f"   ⚠  Colunas de descarte não encontradas: lote={col_lote}, subcateg={col_subcateg}, valor={col_valor}")
        return 0.0

    mask = (df_desc[col_lote] == lote) & (df_desc[col_subcateg].isin(subcategs))
    total = pd.to_numeric(df_desc.loc[mask, col_valor], errors='coerce').sum()
    return round(float(total) if not pd.isna(total) else 0.0, 3)


def solicitar_pm_previsto(lote, data, unid) -> float:
    """Solicita PM Previsto manualmente para cada lote."""
    while True:
        try:
            val = input(f"\n  📝 PM Previsto para Lote {lote} | {unid} | {data}: ").strip().replace(",", ".")
            if val == "":
                print("     (sem valor — usando 0)")
                return 0.0
            return float(val)
        except ValueError:
            print("     ❌ Valor inválido. Digite um número (ex: 0,920)")


def processar(df_rend: pd.DataFrame, df_desc: pd.DataFrame,
              mapa: dict, lote_filtro=None, simulacao=False, pm_manual: dict = None) -> list:
    """Processa cada linha do rendimento e retorna lista de dicts prontos para gravar."""
    resultados = []

    # Garante que temos a coluna Lote
    col_lote = mapa["lote"]
    if not col_lote:
        print("❌ Coluna de Lote não encontrada. Verifique COLS_RENDIMENTO['lote'].")
        return []

    for _, row in df_rend.iterrows():
        lote = row.get(col_lote)
        if pd.isna(lote) or lote == "":
            continue
        lote = str(lote).strip()

        if lote_filtro and lote != str(lote_filtro):
            continue

        data     = row.get(mapa["data"])
        unid     = row.get(mapa["unid_prod"], "")
        bm_prev  = pd.to_numeric(row.get(mapa["bm_prev"]),  errors='coerce') or 0
        bm_real  = pd.to_numeric(row.get(mapa["bm_real"]),  errors='coerce') or 0
        mort_real= pd.to_numeric(row.get(mapa["mort_real"]), errors='coerce') or 0
        pm_real  = pd.to_numeric(row.get(mapa["pm_real"]),  errors='coerce') or 0
        rend_real= pd.to_numeric(row.get(mapa["rend_real"]), errors='coerce') or 0

        # Formata data
        if isinstance(data, datetime):
            data_fmt = data.strftime("%d/%m/%Y")
            data_iso = data.strftime("%Y-%m-%d")
        else:
            data_fmt = str(data) if data else ""
            data_iso = data_fmt

        # Cód. Abate
        cod_abate = f"{data_fmt} - {unid} - {lote}"

        # Descartes
        desc_500g = somar_descarte(df_desc, lote, SUBCATEG_500G)
        desc_bact = somar_descarte(df_desc, lote, SUBCATEG_BACT)
        desc_mole = somar_descarte(df_desc, lote, SUBCATEG_MOLE)

        # Previstos calculados
        desc_500g_prev = round(bm_real * DESC_500G_PERC, 2)
        desc_bact_prev = round(bm_real * DESC_BACT_PERC, 2)
        desc_mole_prev = round(bm_real * DESC_MOLE_PERC, 2)

        # PM Previsto
        chave_pm = f"{lote}_{data_iso}"
        if pm_manual and chave_pm in pm_manual:
            pm_prev = pm_manual[chave_pm]
        elif simulacao:
            pm_prev = 0.0  # não pergunta em simulação
        else:
            pm_prev = solicitar_pm_previsto(lote, data_fmt, unid)
            if pm_manual is not None:
                pm_manual[chave_pm] = pm_prev

        resultado = {
            "Data":               data_fmt,
            "Lote":               lote,
            "Unid. Produtora":    unid,
            "Cód. Abate":         cod_abate,
            "Bm Previsto (kg)":   bm_prev,
            "Bm Realizado (kg)":  bm_real,
            "Δ Bm (kg)":          round(bm_real - bm_prev, 2),
            "Δ Bm (%)":           round((bm_real - bm_prev) / bm_prev * 100, 2) if bm_prev else 0,
            "PM Previsto (kg)":   pm_prev,
            "PM Realizado (kg)":  pm_real,
            "Δ PM (%)":           round((pm_real - pm_prev) / pm_prev * 100, 2) if pm_prev else 0,
            "Rend. Prev (%)":     REND_PREV,
            "Rend. Real (%)":     rend_real,
            "Δ Rend (%)":         round(rend_real - REND_PREV, 2),
            "Mort. Prev (kg)":    MORT_PREV,
            "Mort. Real (kg)":    mort_real,
            "Desc <500g Prev":    desc_500g_prev,
            "Desc <500g Real":    desc_500g,
            "Desc Bact Prev":     desc_bact_prev,
            "Desc Bact Real":     desc_bact,
            "Desc Mole Prev":     desc_mole_prev,
            "Desc Mole Real":     desc_mole,
        }
        resultados.append(resultado)

    return resultados


def imprimir_resultado(resultados: list):
    """Imprime resultado formatado no terminal."""
    if not resultados:
        print("\n⚠  Nenhum resultado processado.")
        return

    print("\n" + "═" * 80)
    print("  RESULTADO — DEVOLUTIVA PISCICULTURAS")
    print("═" * 80)

    for r in resultados:
        print(f"\n  📋 {r['Cód. Abate']}")
        print(f"     Biomassa:   Prev {r['Bm Previsto (kg)']:>8.1f} kg  |  Real {r['Bm Realizado (kg)']:>8.1f} kg  |  Δ {r['Δ Bm (%)']:>+.1f}%")
        print(f"     Rend. Pot.: Prev {r['Rend. Prev (%)']:>7.2f}%   |  Real {r['Rend. Real (%)']:>7.2f}%   |  Δ {r['Δ Rend (%)']:>+.2f}%")
        print(f"     PM:         Prev {r['PM Previsto (kg)']:>8.3f} kg  |  Real {r['PM Realizado (kg)']:>8.3f} kg  |  Δ {r['Δ PM (%)']:>+.1f}%")
        print(f"     Mortalidade:      {r['Mort. Real (kg)']:>8.2f} kg")
        print(f"     Desc <500g: Prev {r['Desc <500g Prev']:>6.2f} kg  |  Real {r['Desc <500g Real']:>6.2f} kg")
        print(f"     Bactéria:   Prev {r['Desc Bact Prev']:>6.2f} kg  |  Real {r['Desc Bact Real']:>6.2f} kg")
        print(f"     Mole:       Prev {r['Desc Mole Prev']:>6.2f} kg  |  Real {r['Desc Mole Real']:>6.2f} kg")


def gravar_excel(resultados: list, caminho: str, aba: str):
    """Adiciona as linhas processadas na aba Executado_Base_Dados."""
    print(f"\n💾 Gravando em: {caminho} → aba '{aba}'")

    try:
        wb = openpyxl.load_workbook(caminho)
    except FileNotFoundError:
        print(f"   ⚠  Arquivo não encontrado, criando novo: {caminho}")
        wb = openpyxl.Workbook()

    if aba not in wb.sheetnames:
        ws = wb.create_sheet(aba)
        # Cabeçalho
        ws.append(list(resultados[0].keys()))
        print(f"   ✅ Aba '{aba}' criada com cabeçalho.")
    else:
        ws = wb[aba]

    # Encontra próxima linha vazia
    proxima = ws.max_row + 1

    lotes_gravados = []
    for r in resultados:
        ws.append(list(r.values()))
        lotes_gravados.append(r["Lote"])

    wb.save(caminho)
    print(f"   ✅ {len(resultados)} linha(s) gravada(s) a partir da linha {proxima}.")
    print(f"   Lotes: {', '.join(lotes_gravados)}")


def inspecionar(caminho_rend: str, caminho_desc: str, aba_desc: str):
    """Modo de inspeção: mostra colunas dos arquivos para validação."""
    print("\n" + "═" * 60)
    print("  MODO INSPEÇÃO — nenhum dado será alterado")
    print("═" * 60)

    print(f"\n📂 {caminho_rend}")
    try:
        df = pd.read_excel(caminho_rend, sheet_name=0, header=0, nrows=3)
        for i, col in enumerate(df.columns):
            letra = ""
            n = i + 1
            while n:
                letra = chr(65 + (n-1) % 26) + letra
                n = (n-1) // 26
            print(f"   {letra:>3} | {col}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    print(f"\n📂 {caminho_desc} → aba '{aba_desc}'")
    try:
        df = pd.read_excel(caminho_desc, sheet_name=aba_desc, header=0, nrows=3)
        for i, col in enumerate(df.columns):
            print(f"   {i+1:>3} | {col}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Coleta dados para Devolutiva Pisciculturas")
    parser.add_argument("--simulacao",   action="store_true", help="Processa mas não grava no Excel")
    parser.add_argument("--inspecionar", action="store_true", help="Mostra estrutura dos arquivos fonte")
    parser.add_argument("--lote",        type=str, default=None, help="Processa somente este lote")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════╗")
    print("║   BTJ Foods — Coleta Devolutiva Pisciculturas    ║")
    print(f"║   {datetime.now().strftime('%d/%m/%Y %H:%M')}                               ║")
    print("╚══════════════════════════════════════════════════╝")

    if args.simulacao:
        print("\n⚠  MODO SIMULAÇÃO — nenhum dado será gravado\n")

    # Modo inspeção
    if args.inspecionar:
        inspecionar(ARQUIVOS["rendimento"], ARQUIVOS["descarte"], ABA_DESCARTE)
        return

    # Verifica arquivos
    erros = []
    for nome, caminho in ARQUIVOS.items():
        if nome == "retorno" and args.simulacao:
            continue
        if not os.path.exists(caminho):
            erros.append(f"  ❌ {nome}: {caminho}")
    if erros:
        print("\nArquivos não encontrados:")
        for e in erros:
            print(e)
        print("\nVerifique se está conectado à rede e tente novamente.")
        sys.exit(1)

    # Leitura
    df_rend = ler_rendimento(ARQUIVOS["rendimento"])
    df_desc = ler_descarte(ARQUIVOS["descarte"], ABA_DESCARTE)

    # Mapeamento de colunas
    mapa = mapear_colunas_rendimento(df_rend)
    print(f"\n🗺  Mapeamento de colunas:")
    for k, v in mapa.items():
        print(f"   {k:12} → {v}")

    # Processamento
    pm_cache = {}
    resultados = processar(df_rend, df_desc, mapa,
                           lote_filtro=args.lote,
                           simulacao=args.simulacao,
                           pm_manual=pm_cache)

    # Exibe resultado
    imprimir_resultado(resultados)

    if not resultados:
        return

    # Grava
    if not args.simulacao:
        confirmar = input(f"\n  Gravar {len(resultados)} linha(s) em Executado_Base_Dados? (s/n): ").strip().lower()
        if confirmar == "s":
            gravar_excel(resultados, ARQUIVOS["retorno"], ABA_DESTINO)
        else:
            print("  Gravação cancelada.")
    else:
        print("\n  (simulação — nada foi gravado)")


if __name__ == "__main__":
    main()
