---
name: apontamento-senior
description: Monta o roteiro passo a passo de preenchimento da tela F909MIF do Senior para apontar produção de uma OP, a partir de apenas três dados (OP, Operador, Quantidade). Use quando Cezaru pedir para apontar produção, lançar produção, apontar uma OP no Senior, ou pedir "apontamento Senior" — mesmo sem citar SQL, banco de dados ou a tela F909MIF.
---

# Apontamento de Produção no Senior (tela F909MIF)

## Objetivo

O apontamento no Senior é **manual** — Cezaru digita direto na tela F909MIF do
sistema. Esta skill não acessa o Senior (não há integração/API configurada);
ela recebe os três dados que variam a cada apontamento (OP, Operador,
Quantidade) e devolve o roteiro completo, já com os campos fixos preenchidos
e o horário calculado, pronto para Cezaru seguir e digitar.

## Dados que Cezaru fornece

Para cada apontamento, Cezaru passa apenas:

- **OP**: número da Ordem de Produção
- **Operador**: matrícula e/ou nome do operador
- **Quantidade**: quantidade da 1ª Qtde a apontar

Se qualquer um dos três não vier, pergunte antes de montar o roteiro.

## Campos fixos da tela F909MIF

Estes valores são sempre os mesmos, salvo Cezaru dizer o contrário:

| Campo | Valor |
|---|---|
| Origem | PAC |
| Tab | 02.0028 |
| Estágio | 1000 |
| Seq. Rot./Opção | 10 |

## Regra do horário

- **Data/Hora Início** e **Data/Hora Fim**: usar a data/hora atual do
  apontamento.
- **O horário (início e fim) tem que ser antes das 17:00.** Se o momento do
  apontamento já passar das 17:00, avisar Cezaru e sugerir usar 16:55 (ou
  horário definido por ele) em vez do horário real, para não estourar o
  limite.
- Fim = Início + 5 minutos (mesmo intervalo do exemplo de referência), salvo
  Cezaru pedir outro intervalo.

## Roteiro a montar

Com OP, Operador e Quantidade em mãos, gerar o roteiro assim:

```
Tela F909MIF

Origem: PAC
(OP/OS) Prod.: <OP> Tab 02.0028
Estágio: 1000
Seq. Rot./Opção: 10
Operador: <matrícula/nome do Operador>
Data/Hora Início: <DD/MM/AAAA HH:MM>   (antes das 17:00)
Data/Hora Fim: <DD/MM/AAAA HH:MM>      (Início + 5 min, antes das 17:00)
Qtde de 1ª Qtde: <Quantidade>
Processar
Sim
Ok
(abre outra tela → clicar no X para fechar)
```

## Passo a passo da skill

1. Perguntar/confirmar OP, Operador e Quantidade se não vierem prontos.
2. Verificar o horário atual; se já passou das 17:00, avisar e propor um
   horário válido (ex.: 16:55) em vez do real.
3. Montar o roteiro completo (acima) com os campos fixos preenchidos.
4. Entregar o roteiro pronto para Cezaru seguir na tela F909MIF.

## Observações

- Esta skill não substitui a digitação manual — ela só monta o roteiro certo
  para reduzir erro e agilizar o preenchimento.
- Se os campos fixos (Origem, Tab, Estágio, Seq. Rot./Opção) mudarem no
  futuro, ou se surgir uma forma de automatizar via navegador/API, atualizar
  esta skill.
