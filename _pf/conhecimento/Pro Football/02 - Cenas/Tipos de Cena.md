---
tags: [pro-football, cenas, assets]
---

# Tipos de Cena
> [!warning] Nota antiga (visão geral A–J, 2026-10-02)
> As letras desta nota **não são mais usadas** no planejamento. O `cenas.json` usa os **códigos da [[Biblioteca de Cenas]]** (60+ variações de 8 vídeos de referência, todas no editor). Para escolher o layout de cada trecho da narração, use a tabela "Que layout usar para cada situação" em [[Da Narração às Cenas]].


Voltar: [[00 - Pro Football (Índice)]] · Relacionado: [[Da Narração às Cenas]] · [[Buscas que Funcionam]]

Catálogo dos layouts que aparecem nos vídeos de referência, com **o que cada um pede de asset**. As letras (A–J) são usadas no `plano.json` (campo `layout`).

| Tipo | % aprox. | Assets que pede | Quando usar |
|---|---|---|---|
| **A. Texto solo** | ~30% | nenhum | frases abstratas, conectivos, opiniões |
| **B. 2 cards lado a lado** | ~25% | 2 fotos/vídeos, de preferência **retrato** | comparações, dois aspectos, processo em 2 passos |
| **C. 1 card central** | ~15% | 1 foto/vídeo **paisagem** | imagem que ilustra a frase inteira |
| **D. Card + texto branco por cima** | ~10% | 1 foto/vídeo | datas, números, frases de ênfase |
| **E. Card + rótulo preto ao lado** | ~8% | 1 foto/logo + texto | **nomes próprios, datas, números** |
| **F. 3 cards** | ~6% | 3 fotos menores | listas, ingredientes, variações |
| **G. Rótulo acima do card** | ~4% | 1 foto + legenda curta | legenda descritiva |
| **H. PNG recortado solto** | ~3% | recorte, bandeira | objeto isolado, bandeiras |
| **I. Mapa** | ~2% | mapa com região destacada | sempre que se cita um lugar |
| **J. Título do item** | 1 por item | **recorte grande** do item | início de cada item |

## A. Texto solo
Frase de 2–6 palavras, preta, centralizada, **1 linha ajustada para ~86% da largura** (frase curta = texto enorme). É a própria narração em pedaços. Cada trecho aparece quando a primeira palavra dele é dita.
> Ex.: "the available passing lanes change" · "These plays demonstrate adaptability"

## B. 2 cards lado a lado
Mesma altura (~780–830 px), gap ~60 px, centralizados. Cada card entra na sua palavra-gatilho. **Peça assets em retrato** (9:16, 3:4): vídeos verticais funcionam muito bem aqui.

## C. 1 card central
Card grande (900–1350 px de largura). Peça **paisagem**. Ideal para vídeo do lance.

## D. Card + texto branco
Texto branco com sombra no centro do card. Pode trocar de frase várias vezes sobre o mesmo card.

## E. Card + rótulo lateral
Card ~45% da tela de um lado, texto preto grande no espaço livre do outro. Padrão para **apresentar um jogador**: foto + nome.

## F. 3 cards
Cards menores (~500–560 px de altura), gap 20–30 px; às vezes 1 grande + 2 empilhados.

## G. Rótulo acima
Texto preto pequeno logo acima do card.

## H. PNG solto
Objeto sem fundo com sombra que segue o contorno (bandeiras, troféu, capacete, bola).

## I. Mapa
Card com mapa e região destacada (laranja/vermelho/verde). Pode entrar **por cima** de outro card já na tela.

## J. Título do item
Nome do item no topo (preto, maiúsculas ~120–130 px) + PNG recortado grande no centro (~900–1000 px), que entra com *scale pop*. Para o Pro Football: **jogador recortado em ação**, troféu, capacete etc.
> [!warning] Recorte do título
> A foto precisa ter **um assunto só**. Se outro jogador estiver encostando, a remoção de fundo leva os dois juntos. Ver [[Log de Aprendizados#2026-10-02 — Teste "Adapting the Pass"]].

## Regras de composição
- O grupo de elementos fica centralizado (x=960, y≈520–540); ocupa 55–85% da largura.
- Elementos **se somam** na cena; nada sai no meio, tudo sai junto.
- Card novo pode entrar por cima de outro (sobreposição).
- Os primeiros cards já entram na posição final do layout completo (não se reorganizam).

Ver também: [[Visual do Formato]] · [[Animação e Ritmo]]
