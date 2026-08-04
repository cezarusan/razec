"""
Coleta automática de dados para Devolutiva Pisciculturas
Lê rendimentoLote3.xlsx e Descarte-ETP.xlsx e grava em Retorno_Pisciculturas.xlsx

Uso:
    python coletar_devolutiva.py                  (interativo)
    python coletar_devolutiva.py --simulacao       (não grava, só mostra resultado)
    python coletar_devolutiva.py --automatico      (sem perguntas — para agendamento)
    python coletar_devolutiva.py --inspecionar     (mostra colunas dos arquivos)
    python coletar_devolutiva.py --lote 2805       (processa só um lote)
"""

import sys
import os
import argparse
import logging
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
    "rendimento":   r"P:\FOODS\CONTROLE DE PRODUÇÃO\Industria\Rendimento_Potencial\rendimentoLote3.xlsx",
    "descarte":     r"P:\FOODS\CONTROLE DE PRODUÇÃO\5 - Descartes\Descarte-ETP.xlsx",
    "retorno":      r"P:\FOODS\PCP\31 - Originação\Retorno_Pisciculturas.xlsx",
    # Arquivo onde o operador preenche o PM Previsto de cada lote antes da execução
    "pm_config":    r"P:\FOODS\PCP\31 - Originação\pm_previsto.xlsx",
    # Cadastro de CodFor → Unid. Produtora (duas colunas: CodFor | Unid. Produtora)
    "codfor_unid":  r"P:\FOODS\PCP\31 - Originação\codfor_unidades.xlsx",
}

# Pasta onde o log diário é gravado
LOG_DIR = r"P:\FOODS\PCP\31 - Originação\logs_devolutiva"

ABA_DESCARTE = "BaseDeDados"
ABA_DESTINO  = "Executado_Base_Dados"

# Colunas do rendimentoLote3.xlsx (índice 0 = coluna A)
# Confirmado via --inspecionar: A=Data, B=SeqLot, C=Lote, D=CodFor
# H=Peso Recebido Est.(BmPrev), I=Peixe Cavalo(BmReal), L=Mortalidade Sangria,
# O=Biometria(PM Real), AA=Rend Pot Bruto
COLS_RENDIMENTO = {
    "lote":      "Lote",       # col C — identificador principal do lote
    "data":      "Data",       # col A
    "codfor":    "CodFor",     # col D — usado para resolver Unid. Produtora via cadastro
    "bm_prev":   "H",          # col H — Biomassa Previsto (Peso Recebido Est.)
    "bm_real":   "I",          # col I — Biomassa Realizado (Peixe Cavalo)
    "mort_real": "L",          # col L — Mortalidade Sangria
    "pm_real":   "O",          # col O — Biometria = PM Realizado
    "rend_real": "AA",         # col AA — Rend. Pot. Bruto
    "idlote":    "idlote",     # col AG — chave numérica usada no Descarte-ETP
}

# Valores fixos
REND_PREV      = 47.50   # % fixo
MORT_PREV      = 0.00    # kg fixo
DESC_500G_PERC = 0.0020  # 0,20% da Biomassa Realizada
DESC_BACT_PERC = 0.0010  # 0,10% da Biomassa Realizada
DESC_MOLE_PERC = 0.0010  # 0,10% da Biomassa Realizada

# Filtros de SubCateg no Descarte-ETP
SUBCATEG_500G  = ["PEIXE INTEIRO < 0,500", "PEIXE SSE < 0,500"]
SUBCATEG_BACT  = ["BACTÉRIA STREPTOCOCCUS", "BACTÉRIA FRANCISELA", "DESCARTE RESÍDUO (BACTÉRIA)"]
SUBCATEG_MOLE  = ["FILE C/COURO MOLE", "FILE REFILADO MOLE", "FILÉ REFILADO MOLE", "DESCARTE RESÍDUO (MOLE)", "PEIXE MOLE"]

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
        "lote":      get_col(COLS_RENDIMENTO["lote"],      2),   # col C
        "data":      get_col(COLS_RENDIMENTO["data"],      0),   # col A
        "codfor":    get_col(COLS_RENDIMENTO["codfor"],    3),   # col D
        "bm_prev":   get_col(COLS_RENDIMENTO["bm_prev"],   col_letra_para_idx("H")),
        "bm_real":   get_col(COLS_RENDIMENTO["bm_real"],   col_letra_para_idx("I")),
        "mort_real": get_col(COLS_RENDIMENTO["mort_real"], col_letra_para_idx("L")),
        "pm_real":   get_col(COLS_RENDIMENTO["pm_real"],   col_letra_para_idx("O")),
        "rend_real": get_col(COLS_RENDIMENTO["rend_real"], col_letra_para_idx("AA")),
        "idlote":    get_col(COLS_RENDIMENTO["idlote"],    col_letra_para_idx("AG")),
    }


def somar_descarte(df_desc: pd.DataFrame, lote, subcategs: list) -> float:
    """Soma PeixeVivoKg para um lote e lista de SubCateg."""
    col_lote = None
    col_subcateg = None
    col_valor = None

    for c in df_desc.columns:
        cl = str(c).lower().replace(" ", "")
        if "lote" in cl and col_lote is None:
            col_lote = c
        if "subcateg" in cl and col_subcateg is None:
            col_subcateg = c
        if "peixevivo" in cl and col_valor is None:
            col_valor = c

    if not col_lote or not col_subcateg or not col_valor:
        logging.warning(f"Colunas de descarte não encontradas: lote={col_lote}, subcateg={col_subcateg}, valor={col_valor}")
        return 0.0

    # Normaliza lote para comparação: converte tudo para string sem decimais
    # Ex: 2805.0 → "2805", "2805" → "2805", 2805 → "2805"
    def _norm_lote(val):
        try:
            return str(int(float(str(val).strip())))
        except (ValueError, TypeError):
            return str(val).strip()

    col_lote_norm = df_desc[col_lote].map(_norm_lote)
    lote_cmp = _norm_lote(lote)
    mask = (col_lote_norm == lote_cmp) & (df_desc[col_subcateg].isin(subcategs))
    total = pd.to_numeric(df_desc.loc[mask, col_valor], errors='coerce').sum()
    return round(float(total) if not pd.isna(total) else 0.0, 3)


def carregar_codfor_unidades() -> dict:
    """
    Lê codfor_unidades.xlsx e retorna dict {codfor: unid_produtora}.
    O arquivo deve ter duas colunas: CodFor | Unid. Produtora
    Se o arquivo não existir, cria um modelo para preenchimento.
    """
    caminho = ARQUIVOS.get("codfor_unid", "")
    if not caminho:
        return {}

    if not os.path.exists(caminho):
        _criar_codfor_modelo(caminho)
        return {}

    try:
        df = pd.read_excel(caminho, sheet_name=0, header=0, dtype=str)
        resultado = {}
        for _, row in df.iterrows():
            codfor = str(row.iloc[0]).strip()
            unid   = str(row.iloc[1]).strip() if len(row) > 1 else ""
            if codfor and unid and codfor.lower() != "nan":
                resultado[codfor] = unid
        logging.info(f"CodFor→Unidade carregado: {len(resultado)} registros")
        return resultado
    except Exception as e:
        logging.warning(f"Não foi possível ler codfor_unidades.xlsx: {e}")
        return {}


def _criar_codfor_modelo(caminho: str):
    """Cria arquivo modelo de codfor_unidades.xlsx para preenchimento."""
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "CodFor Unidades"

        # Cabeçalho
        ws.append(["CodFor", "Unid. Produtora"])

        # Exemplos para orientar preenchimento
        exemplos = [
            ["3",     "BTJ STC"],
            ["4",     "BTJ ILHA"],
            ["13241", "SANTA HELENA"],
            ["10231", "PURO PEIXE"],
        ]
        for ex in exemplos:
            ws.append(ex)

        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 30

        # Instrução na célula D1
        ws["D1"] = "Preencha: CodFor (código do fornecedor) → Unid. Produtora (nome da piscicultura)"

        wb.save(caminho)
        print(f"\n   📄 Arquivo modelo criado: {caminho}")
        print(f"      Preencha o cadastro CodFor → Unid. Produtora antes de rodar.")
    except Exception as e:
        print(f"   ⚠  Não foi possível criar modelo codfor_unidades.xlsx: {e}")


def carregar_pm_config() -> dict:
    """
    Lê pm_previsto.xlsx e retorna dict {lote: pm_previsto}.
    O arquivo deve ter duas colunas: Lote | PM Previsto (kg)
    """
    caminho = ARQUIVOS.get("pm_config", "")
    if not caminho or not os.path.exists(caminho):
        return {}
    try:
        df = pd.read_excel(caminho, sheet_name=0, header=0, dtype=str)
        resultado = {}
        for _, row in df.iterrows():
            lote = str(row.iloc[0]).strip()
            try:
                pm = float(str(row.iloc[1]).replace(",", "."))
                resultado[lote] = pm
            except (ValueError, IndexError):
                pass
        logging.info(f"PM config carregado: {len(resultado)} lotes")
        return resultado
    except Exception as e:
        logging.warning(f"Não foi possível ler pm_previsto.xlsx: {e}")
        return {}


def criar_pm_config_modelo():
    """Cria um arquivo modelo de pm_previsto.xlsx se não existir."""
    caminho = ARQUIVOS.get("pm_config", "")
    if not caminho or os.path.exists(caminho):
        return
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PM Previsto"
        ws.append(["Lote", "PM Previsto (kg)"])
        ws.append(["2805", "0.929"])
        ws.append(["2806", "0.929"])
        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 20
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        wb.save(caminho)
        print(f"   📄 Arquivo modelo criado: {caminho}")
        print(f"      Preencha o PM Previsto de cada lote nesse arquivo antes de rodar.")
    except Exception as e:
        print(f"   ⚠  Não foi possível criar modelo: {e}")


def solicitar_pm_previsto(lote, data, unid, automatico=False) -> float:
    """Solicita PM Previsto manualmente para cada lote (modo interativo)."""
    if automatico:
        logging.warning(f"PM Previsto não encontrado para lote {lote} — usando 0")
        return 0.0
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
              mapa: dict, lote_filtro=None, simulacao=False,
              pm_manual: dict = None, automatico=False,
              codfor_unid: dict = None) -> list:
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
        # Ignora linhas com lote zerado ou inválido (linhas vazias da planilha)
        if lote in ("", "0", "nan", "0.0"):
            continue
        try:
            if int(float(lote)) == 0:
                continue
        except (ValueError, TypeError):
            pass

        if lote_filtro and lote != str(lote_filtro):
            continue

        data   = row.get(mapa["data"])
        codfor = str(row.get(mapa.get("codfor", ""), "")).strip()
        if codfor_unid and codfor in codfor_unid:
            unid = codfor_unid[codfor]
        elif codfor:
            unid = f"CodFor:{codfor}"   # fallback: mostra o código até cadastrar
        else:
            unid = ""
        bm_prev  = pd.to_numeric(row.get(mapa["bm_prev"]),  errors='coerce') or 0
        bm_real  = pd.to_numeric(row.get(mapa["bm_real"]),  errors='coerce') or 0
        mort_real= pd.to_numeric(row.get(mapa["mort_real"]), errors='coerce') or 0
        pm_real  = pd.to_numeric(row.get(mapa["pm_real"]),  errors='coerce') or 0
        rend_real= pd.to_numeric(row.get(mapa["rend_real"]), errors='coerce') or 0
        # Coluna AA armazena decimal (ex: 0.4750 = 47.50%) — converte para %
        if 0 < rend_real < 1:
            rend_real = round(rend_real * 100, 4)
        # idlote é a chave numérica usada no Descarte-ETP (coluna AG do rendimento)
        idlote_raw = row.get(mapa.get("idlote", ""), None)
        if idlote_raw is None or (isinstance(idlote_raw, float) and pd.isna(idlote_raw)):
            idlote = lote
        else:
            idlote = idlote_raw

        # Formata data
        if isinstance(data, datetime):
            data_fmt = data.strftime("%d/%m/%Y")
            data_iso = data.strftime("%Y-%m-%d")
        else:
            data_fmt = str(data) if data else ""
            data_iso = data_fmt

        # Cód. Abate
        cod_abate = f"{data_fmt} - {unid} - {lote}"

        # Descartes — usa idlote (número sequencial) que bate com coluna Lote do Descarte-ETP
        desc_500g = somar_descarte(df_desc, idlote, SUBCATEG_500G)
        desc_bact = somar_descarte(df_desc, idlote, SUBCATEG_BACT)
        desc_mole = somar_descarte(df_desc, idlote, SUBCATEG_MOLE)

        # Previstos calculados
        desc_500g_prev = round(bm_real * DESC_500G_PERC, 2)
        desc_bact_prev = round(bm_real * DESC_BACT_PERC, 2)
        desc_mole_prev = round(bm_real * DESC_MOLE_PERC, 2)

        # PM Previsto — lê do config ou pede manualmente
        if pm_manual and lote in pm_manual:
            pm_prev = pm_manual[lote]
        elif simulacao:
            pm_prev = 0.0
        else:
            pm_prev = solicitar_pm_previsto(lote, data_fmt, unid, automatico=automatico)

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

    # Resumo final
    datas = [r["Data"] for r in resultados if r["Data"]]
    print("\n" + "═" * 80)
    print(f"  RESUMO: {len(resultados)} lote(s) processado(s)")
    if datas:
        print(f"  Período: {min(datas)}  →  {max(datas)}")
    print("═" * 80)


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
        df = pd.read_excel(caminho_desc, sheet_name=aba_desc, header=0)
        for i, col in enumerate(df.columns):
            print(f"   {i+1:>3} | {col}")

        # Mostra SubCateg únicas para validar os filtros
        col_sub = next((c for c in df.columns if "subcateg" in str(c).lower().replace(" ","")), None)
        if col_sub:
            unicas = sorted(df[col_sub].dropna().astype(str).unique())
            print(f"\n   SubCateg encontradas em '{col_sub}' ({len(unicas)} valores únicos):")
            for v in unicas:
                print(f"      • {v}")

        # Mostra formato do lote (início, meio e fim do arquivo)
        col_lote = next((c for c in df.columns if "lote" in str(c).lower()), None)
        if col_lote:
            serie = df[col_lote].dropna().astype(str)
            n = len(serie)
            indices = list(dict.fromkeys([0, 1, 2, n//2, n-3, n-2, n-1]))
            print(f"\n   Exemplos de Lote na coluna '{col_lote}' (total {n} registros):")
            for i in indices:
                if 0 <= i < n:
                    print(f"      linha {i+2}: {serie.iloc[i]}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def configurar_log(automatico: bool):
    """Configura log em arquivo quando roda em modo automático."""
    handlers = [logging.StreamHandler()]
    if automatico:
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            log_file = os.path.join(LOG_DIR, f"devolutiva_{datetime.now().strftime('%Y%m%d')}.log")
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except Exception:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )


def main():
    parser = argparse.ArgumentParser(description="Coleta dados para Devolutiva Pisciculturas")
    parser.add_argument("--simulacao",   action="store_true", help="Processa mas não grava no Excel")
    parser.add_argument("--automatico",  action="store_true", help="Sem perguntas — para agendamento diário")
    parser.add_argument("--inspecionar", action="store_true", help="Mostra estrutura dos arquivos fonte")
    parser.add_argument("--lote",        type=str, default=None, help="Processa somente este lote")
    args = parser.parse_args()

    configurar_log(args.automatico)

    print("╔══════════════════════════════════════════════════╗")
    print("║   BTJ Foods — Coleta Devolutiva Pisciculturas    ║")
    print(f"║   {datetime.now().strftime('%d/%m/%Y %H:%M')}                               ║")
    print("╚══════════════════════════════════════════════════╝")

    if args.simulacao:
        print("\n⚠  MODO SIMULAÇÃO — nenhum dado será gravado\n")
    if args.automatico:
        print("\n🤖 MODO AUTOMÁTICO — sem interação manual\n")

    # Modo inspeção
    if args.inspecionar:
        inspecionar(ARQUIVOS["rendimento"], ARQUIVOS["descarte"], ABA_DESCARTE)
        criar_pm_config_modelo()
        # Cria modelo de cadastro CodFor se não existir
        if not os.path.exists(ARQUIVOS.get("codfor_unid", "")):
            _criar_codfor_modelo(ARQUIVOS["codfor_unid"])
        return

    # Verifica arquivos de entrada
    erros = []
    for nome in ["rendimento", "descarte"]:
        if not os.path.exists(ARQUIVOS[nome]):
            erros.append(f"  ❌ {nome}: {ARQUIVOS[nome]}")
    if not args.simulacao and not os.path.exists(ARQUIVOS["retorno"]):
        erros.append(f"  ❌ retorno: {ARQUIVOS['retorno']}")
    if erros:
        msg = "Arquivos não encontrados:\n" + "\n".join(erros) + "\n\nVerifique a conexão com a rede."
        print(msg)
        logging.error(msg)
        sys.exit(1)

    # Cria modelo de PM se não existir
    criar_pm_config_modelo()

    # Leitura
    df_rend = ler_rendimento(ARQUIVOS["rendimento"])
    df_desc = ler_descarte(ARQUIVOS["descarte"], ABA_DESCARTE)

    # Mapeamento de colunas
    mapa = mapear_colunas_rendimento(df_rend)
    print(f"\n🗺  Mapeamento de colunas:")
    for k, v in mapa.items():
        print(f"   {k:12} → {v}")

    # Cadastro CodFor → Unid. Produtora
    codfor_map = carregar_codfor_unidades()
    if codfor_map:
        print(f"\n🏭 Unidades cadastradas: {', '.join(codfor_map.values())}")
    else:
        print(f"\n⚠  codfor_unidades.xlsx não encontrado ou vazio.")
        print(f"   Preencha o arquivo em: {ARQUIVOS['codfor_unid']}")
        print(f"   Enquanto isso, o campo Unid. Produtora mostrará o código CodFor.")

    # PM Previsto do arquivo de config
    pm_config = carregar_pm_config()
    if pm_config:
        print(f"\n📄 PM Previsto carregado para {len(pm_config)} lote(s): {', '.join(pm_config.keys())}")
    elif args.automatico:
        print(f"\n⚠  pm_previsto.xlsx não encontrado — PM Previsto será 0 para todos os lotes.")
        print(f"   Crie o arquivo em: {ARQUIVOS['pm_config']}")

    # Processamento
    resultados = processar(df_rend, df_desc, mapa,
                           lote_filtro=args.lote,
                           simulacao=args.simulacao,
                           pm_manual=pm_config,
                           automatico=args.automatico,
                           codfor_unid=codfor_map)

    # Exibe resultado
    imprimir_resultado(resultados)

    if not resultados:
        logging.warning("Nenhum resultado processado.")
        return

    # Grava
    if not args.simulacao:
        if args.automatico:
            gravar_excel(resultados, ARQUIVOS["retorno"], ABA_DESTINO)
            logging.info(f"Execução concluída. {len(resultados)} lote(s) gravado(s).")
        else:
            confirmar = input(f"\n  Gravar {len(resultados)} linha(s) em Executado_Base_Dados? (s/n): ").strip().lower()
            if confirmar == "s":
                gravar_excel(resultados, ARQUIVOS["retorno"], ABA_DESTINO)
            else:
                print("  Gravação cancelada.")
    else:
        print("\n  (simulação — nada foi gravado)")


if __name__ == "__main__":
    main()
