---
tags: [bestiario, assets]
---

# Gravuras e Ilustrações

## Os tipos de asset do bestiário
| Tipo | De onde vem | Para quê |
|---|---|---|
| `gravura` | Wikimedia Commons (depois Smithsonian/Openverse): gravura e xilogravura antigas, de domínio público | a lenda como foi desenhada: R1, D1, título |
| `ilustracao` | **gerada** pelo Gemini (Nano Banana), 3 opções por cena, o Claude escolhe | o que a gravura não mostra: o ponto de vista em 2ª pessoa, a escala (E1), a cena do roteiro |
| `foto` / `historica` | Commons, web, Pixabay, Openverse, Smithsonian | o animal, o lugar, o fóssil, o documento real |
| `video` | Pexels, Pixabay (depois Commons, Archive) | o real em movimento: mar, lula, baleia, floresta, neblina |

## Gravuras (Commons, contagem de 2026-11-03)
"sea serpent engraving" 3.749 · Gessner "Historiae animalium" 3.985 · "dragon woodcut" 1.623 · "hydra engraving" 1.015 · "griffin woodcut" 684 · "leviathan engraving" 566 · "basilisk woodcut" 88 · "kraken engraving" 59 · Aberdeen Bestiary 137 páginas · "werewolf woodcut" 18 (lobisomem quase só ilustração).
- Busque com a criatura + `engraving` / `woodcut` / `bestiary` / o nome da obra (Olaus Magnus, Carta Marina, Gessner, Aldrovandi, Pontoppidan, Montfort, Physiologus). **Busca curta** (1–3 palavras): a do Commons exige todas as palavras, e no teste de 2026-11-03 "kraken attacking ship engraving" não achou nada, "giant octopus ship engraving Montfort" achou 1. "Olaus Magnus" traz muitos MAPAS (a Carta Marina e atlas): bom para "sea monster on an old map", ruim para a criatura sozinha.
- O editor inverte o papel (traço preto vira claro sobre o preto) e corta a margem: papel amarelado e manchas não atrapalham. Página com muito texto atrapalha.

## Ilustrações (Gemini)
- Custo: ~US$ 0,05 por imagem (2K), 3 por cena → ~US$ 0,15 por cena ilustrada. Teto de 6 por bloco. Gasto anotado em `<dados>/cache/gemini/gastos.jsonl`.
- O estilo é da ficha (`formato.json › ilustracao.estilo`): scratchboard branco sobre preto, sem texto, sem moldura, nunca pessoa real nem acontecimento real. Uma imagem em `<canal>/identidade/estilo_ilustracao.png` trava o estilo (vai junto em cada pedido).
- O pedido (`descricao`/`buscas` do card) diz SÓ a cena: o que aparece, o ângulo, a escala, a luz. Sem estilo no pedido.
- **Ficha da criatura**: no primeiro bloco, escreva uma frase que descreve a criatura (ex.: "The kraken, a colossal squid-like sea monster with a long mantle, huge round eyes and ten arms covered in hooked suckers") e repita a frase igual em TODO pedido de ilustração dela no vídeo. É o que mantém a mesma criatura de cena a cena.
- E1 (escala): a criatura inteira de lado, isolada, nada mais no quadro.
- Pessoa genérica sem rosto pode (um marinheiro de costas, "you" como mergulhador). Pessoa real, rosto reconhecível ou acontecimento real: não.

## Escolha
Resumida em `prompts/escolher_imagem.md`. Na ilustração: a mais clara e sem deformação, sem letras. Na gravura: antiga de verdade (não arte digital moderna, não estátua, não brinquedo). Franquia nenhuma.
