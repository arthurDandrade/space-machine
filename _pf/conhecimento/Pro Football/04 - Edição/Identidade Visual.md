---
tags: [pro-football, edicao, identidade]
arquivos: /Users/arthur/Canais/ProFootball/identidade/ (logo.webp, banner.webp, thumbnail_exemplo.webp)
---

# Identidade Visual do Canal

Voltar: [[00 - Pro Football (Índice)]] · Relacionado: [[Visual do Formato]] · [[Edição no After Effects]]

Extraída do logo, do banner e de uma thumbnail do canal (cores medidas nos pixels). Aplicada nos vídeos pela **Opção B** (escolhida pelo Arthur em 2026-10-03): identidade nos títulos, nomes e caixas; frases soltas continuam no estilo das referências.

## Cores
| Papel | Cor | Origem |
|---|---|---|
| Fundo | `#EDF0F6` | fundo do logo/banner |
| Texto | `#191A21` (quase-preto) | "INSIDE THE" |
| Azul royal | `#1D2D85` (logo `#2D3D91`) | "NFL WORLD", bola do logo |
| Azul da caixa | `#0B2479` | caixa do "WORK INSIDE" |
| Marinho | `#0B2849` | moldura da thumbnail |
| Sombra | `#0B1A3A` | sombras levemente azuladas |

## Tipografia
- **Marca**: sans condensada pesada, **sempre em MAIÚSCULAS**. No vídeo usamos **Impact** (vem com o Mac; é a mais próxima do banner — a original é um pouco mais condensada).
- Combinação característica: **1ª linha preta + 2ª linha azul** ("INSIDE THE / NFL WORLD").
- Frases soltas (texto solo e rótulos laterais): Avenir Next Heavy, caixa normal, cor `#191A21` (formato das referências).

## Onde aparece no vídeo
| Elemento | Estilo |
|---|---|
| Título de cada tópico | Impact maiúsculo, 2 linhas (preta + azul), quebra antes de palavra de ligação (WHEN, AND, OF…) |
| Nome acima do card (pessoa, comparação) | Impact maiúsculo, `#191A21` |
| Número/termo sobre o card | **caixa azul `#0B2479` + Impact maiúsculo branco** (estilo "WORK INSIDE") |
| Data abaixo de logos | Impact maiúsculo |
| Texto solo / rótulo lateral | Avenir Next Heavy, caixa normal, `#191A21` |
| Fundo | `#EDF0F6` + textura de papel suave + vinheta azulada |
| Elementos de prancheta (X, O, setas, grade "+") | **não usar** (decisão do Arthur) |

## No código
`editor_ae/gerar_ae2.py`: constantes `COR_*` e `FONTE_MARCA`; caixa azul criada como shape layer atrás do texto em `montar_modelo2.jsx`.


## Fundo com adesivos (desde 2026-10-08)
O Arthur trocou o fundo no bloco 01 de [[Who Makes the NFL Possible]]: uma imagem de papel com adesivos de futebol americano nos cantos (bola e jogada desenhada à esquerda em cima, capacete embaixo; campo e X/O à direita em cima, trave embaixo), centro livre para os cards.
- Arquivo: `identidade/fundo_papel_nfl.png` (1672×941).
- No After: camada **"Fundo imagem"** entre o sólido "Fundo" (#EDF0F6) e a "Textura papel"; opacidade **50%**, modo normal, escala **119,6%**, posição **941,6 / 545,3** (os valores que ele deixou no bloco 01).
- Já está no editor (`gerar_ae2.py` → `FUNDO_IMAGEM`; `montar_modelo2.jsx`): todo bloco novo sai com ele. Para trocar a imagem, substitua o arquivo em `identidade/` mantendo o nome.
