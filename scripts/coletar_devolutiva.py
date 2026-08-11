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
import glob
import argparse
import json
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
    "retorno":      r"P:\FOODS\PCP\31 - Originacao\Retorno_Pisciculturas.xlsx",
    # Arquivo onde o operador preenche o PM Previsto de cada lote antes da execução
    "pm_config":    r"P:\FOODS\PCP\31 - Originacao\pm_previsto.xlsx",
    # Cadastro de CodFor → Unid. Produtora (duas colunas: CodFor | Unid. Produtora)
    "codfor_unid":  r"P:\FOODS\PCP\31 - Originacao\codfor_unidades.xlsx",
    # Biomassa Previsto — colunas: DATA | LOTE(seq) | Fornecedor | Qt. Fornecedor (col D)
    "bm_previsto":  r"P:\FOODS\PCP\31 - Originacao\Indicadores - Doc. recepção pescado.xlsx",
}

# Pasta onde o log diário é gravado
LOG_DIR = r"P:\FOODS\PCP\31 - Originacao\logs_devolutiva"

# Caminho do JSON exportado para o dashboard
JSON_EXPORT = r"P:\FOODS\PCP\31 - Originacao\devolutiva_dados.json"

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
    "bm_prev":   "",           # Previsto Biomassa a definir — mantido zero até confirmar fonte
    "bm_real":   "H",          # col H — Peso Recebido (Realizado confirmado pelo usuário)
    "mort_real": "L",          # col L — Mortalidade Sangria
    "pm_real":   "O",          # col O — Biometria = PM Realizado
    "rend_real": "AA",         # col AA — Rend. Pot. Bruto
    "seqlot":    "SeqLot",     # col B — sequência do abate no dia, igual a Lote no Descarte-ETP
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


def achar_pasta() -> str:
    """Localiza a pasta de Originação na rede, tolerando variações de acento."""
    for p in [r"P:\FOODS\PCP\31 - Originação", r"P:\FOODS\PCP\31 - Originacao"]:
        if os.path.isdir(p):
            return p
    for p in glob.glob(r"P:\FOODS\PCP\31*"):
        if os.path.isdir(p):
            return p
    return None


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
        "seqlot":    get_col(COLS_RENDIMENTO["seqlot"],    col_letra_para_idx("B")),
    }


def _norm_data(val):
    if isinstance(val, datetime):
        return val.date()
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return str(val)


def construir_indice_descarte(df_desc: pd.DataFrame) -> dict:
    """
    Pré-processa o Descarte-ETP em um dicionário:
    { (data, seqlot, subcateg): total_peixevivokg }
    SeqLot do Descarte-ETP (col Lote, valores 1/2/3 por dia) bate com SeqLot do rendimento.
    """
    col_data = col_lote = col_subcateg = col_valor = None
    for c in df_desc.columns:
        cl = str(c).lower().replace(" ", "")
        if cl == "data" and col_data is None:
            col_data = c
        if cl == "lote" and col_lote is None:
            col_lote = c
        if "subcateg" in cl and col_subcateg is None:
            col_subcateg = c
        if "peixevivo" in cl and col_valor is None:
            col_valor = c

    if not col_data or not col_lote or not col_subcateg or not col_valor:
        return {}

    idx = {}
    for _, row in df_desc.iterrows():
        d = _norm_data(row[col_data])
        try:
            seq = int(float(str(row[col_lote]).strip()))
        except (ValueError, TypeError):
            continue
        sub = str(row[col_subcateg]).strip() if pd.notna(row[col_subcateg]) else ""
        val = pd.to_numeric(row[col_valor], errors='coerce')
        if pd.isna(val):
            val = 0.0
        key = (d, seq, sub)
        idx[key] = idx.get(key, 0.0) + float(val)
    return idx


def somar_descarte_idx(indice: dict, data, seqlot, subcategs: list) -> float:
    """Soma descartes para Data + SeqLot + SubCateg."""
    d = _norm_data(data)
    try:
        seq = int(float(str(seqlot).strip()))
    except (ValueError, TypeError):
        return 0.0
    total = sum(indice.get((d, seq, sub), 0.0) for sub in subcategs)
    return round(total, 3)


def carregar_codfor_unidades() -> dict:
    """
    Lê codfor_unidades.xlsx e retorna dict {codfor: unid_produtora}.
    O arquivo deve ter duas colunas: CodFor | Unid. Produtora
    Se o arquivo não existir, cria um modelo para preenchimento.
    """
    caminho = ARQUIVOS.get("codfor_unid", "")
    if not caminho or not os.path.exists(caminho):
        pasta = achar_pasta()
        if pasta:
            caminho = os.path.join(pasta, "codfor_unidades.xlsx")
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
    Lê pm_previsto.xlsx.
    Formato novo (prioritário): Semana | Unid. Produtora | PM Previsto (kg)
      → retorna {(semana_int, unid): pm}  e  {unid: pm}  (média por unidade)
    Formato legado: Lote | PM Previsto (kg)
      → retorna {lote_str: pm}
    Todos os formatos coexistem no mesmo dict de retorno.
    """
    # Tenta o caminho fixo primeiro; se não achar, usa achar_pasta() dinâmico
    caminho = ARQUIVOS.get("pm_config", "")
    if not caminho or not os.path.exists(caminho):
        pasta = achar_pasta()
        if pasta:
            caminho = os.path.join(pasta, "pm_previsto.xlsx")
    if not caminho or not os.path.exists(caminho):
        return {}
    try:
        df = pd.read_excel(caminho, sheet_name=0, header=0, dtype=str)
        cols = [str(c).strip().lower() for c in df.columns]
        resultado = {}

        # Formato novo: 3 colunas — Semana | Unid. Produtora | PM Previsto
        if len(df.columns) >= 3 and any("sem" in c for c in cols):
            for _, row in df.iterrows():
                sem_str  = str(row.iloc[0]).strip()
                unid     = str(row.iloc[1]).strip().replace('\xa0', ' ')
                pm_str   = str(row.iloc[2]).strip().replace(",", ".")
                if sem_str.lower() in ("nan", "") or unid.lower() in ("nan", ""):
                    continue
                try:
                    sem = int(float(sem_str))
                    pm  = float(pm_str)
                    resultado[(sem, unid)] = pm   # lookup preciso
                    # fallback por unidade (último valor vence — usa a mais recente)
                    resultado[unid] = pm
                except (ValueError, TypeError):
                    pass
        else:
            # Formato legado: Lote | PM Previsto
            for _, row in df.iterrows():
                lote = str(row.iloc[0]).strip()
                try:
                    pm = float(str(row.iloc[1]).replace(",", "."))
                    resultado[lote] = pm
                except (ValueError, IndexError):
                    pass
            logging.info(f"PM config (por Lote) carregado: {len(resultado)} lotes")

        return resultado
    except Exception as e:
        logging.warning(f"Não foi possível ler pm_previsto.xlsx: {e}")
        return {}


def carregar_bm_previsto() -> dict:
    """
    Lê 'Indicadores - Doc. recepção pescado.xlsx'.
    Colunas esperadas: DATA | LOTE (seq 1/2/3) | Fornecedor | Qt. Fornecedor
    Retorna dict { (date, seq_int): qt_fornecedor_kg }
    """
    caminho = ARQUIVOS.get("bm_previsto", "")
    print(f"\n[BM] Procurando arquivo em: {caminho}")
    if not caminho or not os.path.exists(caminho):
        # Tenta pasta Qualidade com variações de nome (com/sem acento)
        pasta_qual = r"P:\FOODS\QUALIDADE\35 - Indicadores da Qualidade"
        nomes = [
            "Indicadores - Doc. recepção pescado.xlsx",
            "Indicadores - Doc. recepcao pescado.xlsx",
            "Indicadores - Doc. recep\u00e7\u00e3o pescado.xlsx",
        ]
        for pasta in [pasta_qual, achar_pasta()]:
            if not pasta or not os.path.isdir(pasta):
                continue
            # Lista todos os arquivos da pasta para diagnóstico
            try:
                arqs = [f for f in os.listdir(pasta) if "indicador" in f.lower() or "recepcao" in f.lower() or "recep" in f.lower()]
                if arqs:
                    print(f"[BM] Arquivos encontrados em {pasta}: {arqs}")
            except Exception:
                pass
            for nome in nomes:
                c = os.path.join(pasta, nome)
                if os.path.exists(c):
                    caminho = c
                    print(f"[BM] Arquivo encontrado: {c}")
                    break
            if caminho and os.path.exists(caminho):
                break
    if not caminho or not os.path.exists(caminho):
        print(f"[BM] ARQUIVO NAO ENCONTRADO — Biomassa Previsto sera 0")
        return {}
    try:
        df = pd.read_excel(caminho, sheet_name=0, header=0)
        resultado = {}
        col_data = col_lote = col_qt = None
        for c in df.columns:
            cl = str(c).strip().lower().replace(" ", "").replace(".", "")
            if col_data is None and cl == "data":
                col_data = c
            if col_lote is None and cl == "lote":
                col_lote = c
            if col_qt is None and "qtfornecedor" in cl:
                col_qt = c
        # fallback posicional se nomes não baterem: DATA=col0, LOTE=col1, Qt.Forn=col3
        if col_data is None and len(df.columns) > 0:
            col_data = df.columns[0]
        if col_lote is None and len(df.columns) > 1:
            col_lote = df.columns[1]
        if col_qt is None and len(df.columns) > 3:
            col_qt = df.columns[3]
        if not col_data or not col_lote or not col_qt:
            logging.warning(f"Colunas não encontradas em bm_previsto: data={col_data} lote={col_lote} qt={col_qt}")
            return {}
        for _, row in df.iterrows():
            d = _norm_data(row[col_data])
            try:
                seq = int(float(str(row[col_lote]).strip()))
                # Usa pd.to_numeric primeiro — se o pandas já leu como número, usa direto
                # sem string manipulation que corromperia "5022.0" → "50220"
                qt_raw = row[col_qt]
                qt = pd.to_numeric(qt_raw, errors='coerce')
                if pd.isna(qt):
                    # Só faz replace se vier como texto com separador de milhar (ex: "5.022")
                    qt = float(str(qt_raw).replace(".", "").replace(",", "."))
                qt = float(qt)
                if seq > 0 and qt > 0:
                    resultado[(d, seq)] = qt
            except (ValueError, TypeError):
                pass
        print(f"   Bm Previsto: cols detectadas → data='{col_data}' lote='{col_lote}' qt='{col_qt}'")
        print(f"   Bm Previsto: {len(resultado)} registros carregados")
        if resultado:
            exemplo = next(iter(resultado.items()))
            print(f"   Exemplo: {exemplo}")
        return resultado
    except Exception as e:
        logging.warning(f"Não foi possível ler bm_previsto: {e}")
        return {}


def criar_pm_config_modelo(unidades: list = None):
    """
    Cria pm_previsto.xlsx com formato Semana × Unid. Produtora.
    Se o arquivo já existir, não sobrescreve.
    """
    caminho = ARQUIVOS.get("pm_config", "")
    if not caminho or os.path.exists(caminho):
        return
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PM Previsto"

        # Cabeçalho
        header = ["Semana", "Unid. Produtora", "PM Previsto (kg)"]
        ws.append(header)

        # Estilo do cabeçalho
        from openpyxl.styles import PatternFill, Font, Alignment
        hdr_fill = PatternFill("solid", fgColor="1F4E79")
        hdr_font = Font(bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = Alignment(horizontal="center")

        # Linhas de exemplo com as unidades cadastradas (ou padrão)
        if not unidades:
            unidades = ["BTJ STC", "BTJ ILHA", "BTJ SUD", "SANTA HELENA", "PURO PEIXE"]

        from datetime import date
        semana_atual = date.today().isocalendar()[1]
        for sem in range(max(1, semana_atual - 1), semana_atual + 3):
            for unid in unidades:
                ws.append([sem, unid, 0.929])

        ws.column_dimensions["A"].width = 12
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["C"].width = 20

        # Instrução
        ws["E1"] = "Preencha o PM Previsto (kg/peixe) para cada Semana e Unidade Produtora"
        ws["E1"].font = Font(italic=True, color="555555")
        ws.column_dimensions["E"].width = 60

        wb.save(caminho)
        print(f"\n   📄 Planilha PM Previsto criada: {caminho}")
        print(f"      Preencha o PM esperado por semana e unidade produtora.")
    except Exception as e:
        print(f"   ⚠  Não foi possível criar pm_previsto.xlsx: {e}")


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
              codfor_unid: dict = None, data_inicio=None,
              bm_previsto: dict = None) -> list:
    """Processa cada linha do rendimento e retorna lista de dicts prontos para gravar."""
    resultados = []

    # Pré-processa descarte em índice por data
    indice_desc = construir_indice_descarte(df_desc)

    # Conta quantos lotes válidos existem por data no rendimento
    col_lote = mapa["lote"]
    col_data_rend = mapa["data"]
    lotes_por_dia: dict = {}
    for _, row in df_rend.iterrows():
        l = row.get(col_lote)
        if pd.isna(l) or str(l).strip() in ("", "0", "nan", "0.0"):
            continue
        d = _norm_data(row.get(col_data_rend))
        lotes_por_dia[d] = lotes_por_dia.get(d, 0) + 1

    # Garante que temos a coluna Lote
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

        if data_inicio:
            data_row = _norm_data(row.get(mapa["data"]))
            if data_row and data_row < data_inicio:
                continue

        data   = row.get(mapa["data"])
        codfor = str(row.get(mapa.get("codfor", ""), "")).strip()
        if codfor_unid and codfor in codfor_unid:
            unid = codfor_unid[codfor]
        elif codfor:
            unid = f"CodFor:{codfor}"   # fallback: mostra o código até cadastrar
        else:
            unid = ""
        # bm_prev vem do arquivo "Indicadores - Doc. recepção pescado" por (data, seqlot)
        _data_norm = _norm_data(row.get(mapa["data"]))
        _seq_tmp   = row.get(mapa.get("seqlot", ""), None)
        try:
            _seq_tmp = int(float(str(_seq_tmp).strip())) if _seq_tmp is not None else 0
        except (ValueError, TypeError):
            _seq_tmp = 0
        bm_prev = (bm_previsto or {}).get((_data_norm, _seq_tmp), 0.0)
        bm_real  = pd.to_numeric(row.get(mapa["bm_real"]),  errors='coerce') or 0
        mort_real= pd.to_numeric(row.get(mapa["mort_real"]), errors='coerce') or 0
        pm_real  = pd.to_numeric(row.get(mapa["pm_real"]),  errors='coerce') or 0
        rend_real= pd.to_numeric(row.get(mapa["rend_real"]), errors='coerce') or 0
        # Coluna AA armazena decimal (ex: 0.4750 = 47.50%) — converte para %
        if 0 < rend_real < 1:
            rend_real = round(rend_real * 100, 4)
        seqlot = row.get(mapa.get("seqlot", ""), None)

        # Formata data
        if isinstance(data, datetime):
            data_fmt = data.strftime("%d/%m/%Y")
            data_iso = data.strftime("%Y-%m-%d")
        else:
            data_fmt = str(data) if data else ""
            data_iso = data_fmt

        # Cód. Abate
        cod_abate = f"{data_fmt} - {unid} - {lote}"

        # Descartes — junta por Data + SeqLot (= Lote no Descarte-ETP, valor 1/2/3 por dia)
        desc_500g = somar_descarte_idx(indice_desc, data, seqlot, SUBCATEG_500G)
        desc_bact = somar_descarte_idx(indice_desc, data, seqlot, SUBCATEG_BACT)
        desc_mole = somar_descarte_idx(indice_desc, data, seqlot, SUBCATEG_MOLE)

        # Previstos calculados
        desc_500g_prev = round(bm_real * DESC_500G_PERC, 2)
        desc_bact_prev = round(bm_real * DESC_BACT_PERC, 2)
        desc_mole_prev = round(bm_real * DESC_MOLE_PERC, 2)

        # Semana ISO e sequência para o dashboard
        try:
            sem = _norm_data(data).isocalendar()[1] if data else 0
        except Exception:
            sem = 0

        # PM Previsto — lookup por (semana, unidade) > unidade > lote
        pm_prev = 0.0
        if pm_manual:
            if (sem, unid) in pm_manual:
                pm_prev = pm_manual[(sem, unid)]
            elif unid in pm_manual:
                pm_prev = pm_manual[unid]
            elif lote in pm_manual:
                pm_prev = pm_manual[lote]
        if pm_prev == 0.0 and not simulacao:
            pm_prev = solicitar_pm_previsto(lote, data_fmt, unid, automatico=automatico)
        try:
            seq_int = int(float(str(seqlot).strip())) if seqlot is not None else 0
        except (ValueError, TypeError):
            seq_int = 0

        resultado = {
            "Data":               data_fmt,
            "Data ISO":           data_iso,
            "Semana":             sem,
            "SeqLote":            seq_int,
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


def gravar_json(resultados: list, caminho: str):
    """
    Exporta os resultados para JSON no formato esperado pelo dashboard.
    Campos: data, data_iso, sem, seq, prod, lote, cod,
            bm_prev, bm_real, pm_prev, pm_real,
            rend_prev, rend_real, mort_prev, mort_real,
            desc500g_prev, desc500g_real, bact_prev, bact_real, mole_prev, mole_real
    """
    registros = []
    for r in resultados:
        registros.append({
            "data":          r.get("Data ISO", ""),
            "data_fmt":      r.get("Data", ""),
            "sem":           r.get("Semana", 0),
            "seq":           r.get("SeqLote", 0),
            "prod":          r.get("Unid. Produtora", ""),
            "lote":          r.get("Lote", ""),
            "cod":           r.get("Cód. Abate", ""),
            "bm_prev":       r.get("Bm Previsto (kg)", 0),
            "bm_real":       r.get("Bm Realizado (kg)", 0),
            "pm_prev":       r.get("PM Previsto (kg)", 0),
            "pm_real":       r.get("PM Realizado (kg)", 0),
            "rend_prev":     r.get("Rend. Prev (%)", 0),
            "rend_real":     r.get("Rend. Real (%)", 0),
            "mort_prev":     r.get("Mort. Prev (kg)", 0),
            "mort_real":     r.get("Mort. Real (kg)", 0),
            "desc500g_prev": r.get("Desc <500g Prev", 0),
            "desc500g_real": r.get("Desc <500g Real", 0),
            "bact_prev":     r.get("Desc Bact Prev", 0),
            "bact_real":     r.get("Desc Bact Real", 0),
            "mole_prev":     r.get("Desc Mole Prev", 0),
            "mole_real":     r.get("Desc Mole Real", 0),
        })

    payload = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "versao":    "2026-08-04-v9",
        "total":     len(registros),
        "registros": registros,
    }

    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON exportado: {caminho}  ({len(registros)} registros)")
        logging.info(f"JSON exportado: {caminho}  ({len(registros)} registros)")
    except Exception as e:
        print(f"\n⚠  Não foi possível gravar JSON: {e}")
        logging.warning(f"Erro ao gravar JSON: {e}")


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
    parser.add_argument("--simulacao",    action="store_true", help="Processa mas não grava no Excel")
    parser.add_argument("--automatico",   action="store_true", help="Sem perguntas — para agendamento diário")
    parser.add_argument("--inspecionar",  action="store_true", help="Mostra estrutura dos arquivos fonte")
    parser.add_argument("--lote",         type=str, default=None, help="Processa somente este lote")
    parser.add_argument("--data-inicio",  type=str, default=None, dest="data_inicio",
                        help="Processa somente lotes a partir desta data (DD/MM/AAAA ou AAAA-MM-DD)")
    parser.add_argument("--ultimos",      type=int, default=100,
                        help="Mostra somente os últimos N lotes (por data) — padrão: 100")
    parser.add_argument("--exportar-json", action="store_true", dest="exportar_json",
                        help="Exporta resultado para JSON (para o dashboard HTML)")
    args = parser.parse_args()

    configurar_log(args.automatico)

    print("╔══════════════════════════════════════════════════╗")
    print("║   BTJ Foods — Coleta Devolutiva Pisciculturas    ║")
    print(f"║   {datetime.now().strftime('%d/%m/%Y %H:%M')}                               ║")
    print("║   versao: 2026-08-04-v12                         ║")
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

    # Cria modelo de PM se não existir (após carregar unidades para pré-preencher)
    unidades_lista = list(codfor_map.values()) if codfor_map else []
    criar_pm_config_modelo(unidades=unidades_lista or None)
    if codfor_map:
        print(f"\n🏭 Unidades cadastradas: {', '.join(codfor_map.values())}")
    else:
        print(f"\n⚠  codfor_unidades.xlsx não encontrado ou vazio.")
        print(f"   Preencha o arquivo em: {ARQUIVOS['codfor_unid']}")
        print(f"   Enquanto isso, o campo Unid. Produtora mostrará o código CodFor.")

    # PM Previsto do arquivo de config
    pm_config = carregar_pm_config()
    if pm_config:
        entradas = [f"{k}" for k in pm_config.keys() if isinstance(k, tuple)]
        unids    = [k for k in pm_config.keys() if isinstance(k, str)]
        if entradas:
            print(f"\n📄 PM Previsto carregado: {len(entradas)} combinações Semana×Unidade")
        else:
            print(f"\n📄 PM Previsto carregado para {len(unids)} lote(s)")
    elif args.automatico:
        print(f"\n⚠  pm_previsto.xlsx não encontrado — PM Previsto será 0 para todos os lotes.")
        print(f"   Crie o arquivo em: {ARQUIVOS['pm_config']}")

    # Filtro de data início
    data_inicio = None
    if args.data_inicio:
        try:
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    data_inicio = datetime.strptime(args.data_inicio, fmt).date()
                    break
                except ValueError:
                    continue
            if not data_inicio:
                print(f"⚠  Data inválida: {args.data_inicio}. Use DD/MM/AAAA ou AAAA-MM-DD.")
        except Exception:
            pass

    # Biomassa Previsto do arquivo Indicadores - Doc. recepção pescado
    bm_prev_map = carregar_bm_previsto()
    if bm_prev_map:
        print(f"\n⚖  Bm Previsto carregado: {len(bm_prev_map)} registros")
    else:
        print(f"\n⚠  Bm Previsto não encontrado — verifique: {ARQUIVOS.get('bm_previsto','')}")

    # Processamento
    resultados = processar(df_rend, df_desc, mapa,
                           lote_filtro=args.lote,
                           simulacao=args.simulacao,
                           pm_manual=pm_config,
                           automatico=args.automatico,
                           codfor_unid=codfor_map,
                           data_inicio=data_inicio,
                           bm_previsto=bm_prev_map)

    # Filtro --ultimos N (padrão 100)
    if args.ultimos and resultados:
        resultados_ord = sorted(resultados, key=lambda r: r["Data ISO"])
        resultados = resultados_ord[-args.ultimos:]

    # Exibe resultado
    imprimir_resultado(resultados)

    if not resultados:
        logging.warning("Nenhum resultado processado.")
        return

    # Exporta JSON para o dashboard (automático ou flag explícita)
    if args.automatico or args.exportar_json:
        gravar_json(resultados, JSON_EXPORT)

    # Grava Excel
    if not args.simulacao:
        if args.automatico:
            gravar_excel(resultados, ARQUIVOS["retorno"], ABA_DESTINO)
            logging.info(f"Execução concluída. {len(resultados)} lote(s) gravado(s).")
        else:
            confirmar = input(f"\n  Gravar {len(resultados)} linha(s) em Executado_Base_Dados? (s/n): ").strip().lower()
            if confirmar == "s":
                gravar_excel(resultados, ARQUIVOS["retorno"], ABA_DESTINO)
                # Exporta JSON também ao gravar manualmente
                if not (args.automatico or args.exportar_json):
                    gravar_json(resultados, JSON_EXPORT)
            else:
                print("  Gravação cancelada.")
    else:
        print("\n  (simulação — nada foi gravado)")


if __name__ == "__main__":
    main()
