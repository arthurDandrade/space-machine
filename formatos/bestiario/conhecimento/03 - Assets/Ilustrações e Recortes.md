---
tags: [bestiario, assets]
---

# Ilustrações e Recortes

## Os tipos de asset do bestiário
| Tipo | De onde vem | Para quê |
|---|---|---|
| `recorte` | **gerado** pelo Gemini (Nano Banana, fonte `gemini_recorte`) em fundo liso, 3 opções, o Claude escolhe, o `finalizar.py` tira o fundo (rembg) | a criatura, o "você", o ícone (elefante, barco), o objeto |
| `ilustracao` | **gerado** (fonte `gemini`) | cenário de fundo, sem a criatura, com espaço vazio no meio (card com `"fundo": true`) |
| `gravura` | Wikimedia Commons (depois Smithsonian/Openverse): gravura e xilogravura antigas, de domínio público | dentro do documento (D1): "como desenharam em 1555" |
| `foto` / `historica` / `video` | Commons, web, Pixabay, Pexels, Openverse, Smithsonian, Archive | o real (R1, S1): o animal que inspirou a lenda, o lugar, o fóssil |

## O elenco do vídeo (a mesma criatura do começo ao fim)
Card com `"elenco": "kraken"`: a 1ª vez ele é gerado e escolhido como qualquer recorte; o `finalizar.py` guarda a escolhida em `<vídeo>/elenco/kraken.png`, e todo bloco compilado depois usa esse arquivo (vira `"arquivo"`, sem busca e sem custo). Dentro do mesmo bloco, os outros cards com o mesmo elenco reusam o 1º asset. Pose diferente = outro nome ("kraken-boca-aberta"). Para trocar a criatura do vídeo, apague o arquivo do elenco e refaça a busca do bloco que a gerou.

## Estilo
- `formato.json › ilustracao.estilo_recorte`: vetorial 2D chapado, formas limpas, sombra simples, luz de cima à esquerda, o assunto inteiro centralizado em fundo cinza-claro liso, sem chão, sem sombra, sem texto; nunca pessoa real.
- `formato.json › ilustracao.estilo`: o mesmo traço para cenário largo, paleta escura (azul-petróleo, marinho, ardósia), espaço vazio no meio, sem criatura nem gente.
- Uma imagem em `<canal>/identidade/estilo_ilustracao.png` trava o estilo do canal (vai junto em cada pedido). Um `<canal>/identidade/personagem.png` (recorte) vira o "você" de todas as cenas.
- O pedido (`buscas` do card) diz SÓ a cena: a criatura e a pose, sempre **"full body, side view facing right, isolated"** (o editor espelha quando ela nada para a esquerda).

## Custo
~US$ 0,05 por imagem (2K), 3 por pedido → ~US$ 0,15 por recorte/cenário novo; o elenco sai uma vez por vídeo. Teto de 6 pedidos novos por bloco. Gasto em `<dados>/cache/gemini/gastos.jsonl`. No Flow (labs.google), com o plano do Arthur, o Nano Banana 2.1 sai por 0 créditos — mas só pelo navegador (não tem API). Teste de 2026-11-03: logo depois de gerar, cada imagem tem um link assinado em `flow-content.google` (1024×1024 no 1:1) que baixa sem login; depois de recarregar a página o Flow passa a servir por `flow.google.com/asb/...`, que exige a sessão — então baixe na hora. O botão de download do Flow e downloads pelo navegador do app não chegam em ~/Downloads. A escolha entra no bloco por `escolhas.json` com `"arquivo"` (o `finalizar.py` recorta e guarda no elenco).

## Gravuras (Commons, contagem de 2026-11-03)
"sea serpent engraving" 3.749 · Gessner 3.985 · "dragon woodcut" 1.623 · "hydra engraving" 1.015 · "griffin woodcut" 684 · "leviathan engraving" 566 · "basilisk woodcut" 88 · "kraken engraving" 59. **Busca curta** (1–3 palavras: a do Commons exige todas) — "kraken Montfort", "sea serpent Olaus Magnus". "Olaus Magnus" traz muitos MAPAS.

## Escolha
Resumida em `prompts/escolher_imagem.md`. Recorte: inteiro, olhando para a direita, sem deformação, sem letras, fundo liso separado do assunto; com elenco, vale para o vídeo todo. Franquia nenhuma.
