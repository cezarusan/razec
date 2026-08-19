---
name: apontamento-senior
description: Organiza os dados de produção (Filetagem e Refile) vindos do banco ERP em uma lista clara e conferida, pronta para o operador digitar manualmente no sistema Senior. Use quando Cezaru pedir para preparar, conferir ou organizar o apontamento de produtos do dia/turno para lançar no Senior, ou pedir "apontamento Senior", "lançar produção no Senior", "lista de apontamento" — mesmo sem citar SQL ou o banco de dados.
---

# Apontamento de Produtos no Senior

## Objetivo

O lançamento no Senior é **manual** (o operador digita direto no sistema). Esta
skill não acessa o Senior — ela prepara os dados de origem (banco ERP
`BTJDW.industriafrigo`, as mesmas tabelas usadas nos dashboards deste
repositório) em uma lista organizada, conferida e fácil de digitar, reduzindo
erro de leitura e retrabalho na hora do apontamento manual.

## Quando usar

- Cezaru pede para "preparar o apontamento de hoje/do turno para o Senior"
- Pede para conferir os apontamentos antes de lançar
- Pede uma lista/checklist de lotes, caixas, pesos e operadores para digitar

## Fontes de dados

As mesmas tabelas usadas em `dashboards/apontamentos-btj.html` e
`dashboards/apontamentos-geral.json`:

- `BTJDW.industriafrigo.ApontamentoCaixaFiletagem`
- `BTJDW.industriafrigo.ApontamentoCaixaRefile`

Campos relevantes: `DataInicio`, `Lote` (só Filetagem), `HoraFim`, `Operador`,
`CodigoCaixa`, `PesoInicial`, `PesoFinal`, `PesoResiduo`, situação `= 'F'`
(finalizado).

Rendimento:
- Filetagem: `PesoFinal / (PesoInicial - PesoResiduo) * 100`
- Refile: `(PesoFinal + PesoResiduo) / PesoInicial * 100`

Se não houver acesso direto ao banco na sessão, peça a Cezaru para colar o
resultado da consulta (ex.: export do Grafana/SSMS) e trabalhe a partir disso.

## Passo a passo

1. **Definir o período**: confirmar com Cezaru a data/turno (padrão: dia
   atual) e o setor (Filetagem, Refile, ou ambos).
2. **Obter os dados**: rodar a consulta equivalente à do dashboard para o
   período pedido, filtrando `situacao = 'F'` e excluindo operador de teste
   (`Operador <> 667`). Se não houver acesso ao banco, pedir os dados brutos
   a Cezaru.
3. **Organizar por operador**: agrupar os registros por `Operador`, em ordem
   cronológica (`HoraFim`), destacando:
   - Lote (Filetagem) / Código da Caixa
   - Peso Inicial, Peso Final, Peso Resíduo
   - Rendimento calculado (%)
4. **Sinalizar inconsistências** antes de entregar a lista, para conferência
   manual no Senior:
   - Rendimento fora da faixa normal (ex.: < 50% ou > 100%) — sinalizar como
     possível erro de digitação de peso
   - Peso Final ou Peso Inicial zerado/ausente
   - Registros duplicados (mesmo Lote/CodigoCaixa e operador no mesmo minuto)
5. **Entregar a lista pronta para digitação**, em formato de tabela simples
   (texto ou markdown), agrupada por operador, na ordem em que aparecem no
   Senior (data/hora), com uma coluna final de "OK ✔" em branco para o
   operador marcar conforme digita.

## Formato de saída sugerido

```
OPERADOR: <nome/matrícula>
| Hora  | Lote/Caixa | Peso Inicial | Peso Final | Resíduo | Rendimento | OK |
|-------|------------|--------------|------------|---------|------------|----|
| 08:12 | 4521       | 32,4         | 18,1       | 0,6     | 56,8%      |    |
...
⚠ Observações: <linhas sinalizadas e o motivo>
```

Repetir por operador, na ordem de aparição no período.

## Observações

- Não é objetivo desta skill automatizar o lançamento no Senior (não há
  integração/API configurada) — o resultado é sempre uma lista de apoio para
  digitação manual.
- Se no futuro surgir um layout de importação em massa do Senior (arquivo
  modelo), atualizar esta skill para gerar esse arquivo diretamente em vez
  da lista de conferência.
