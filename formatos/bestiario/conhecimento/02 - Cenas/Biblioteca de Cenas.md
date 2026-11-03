---
tags: [bestiario, cenas]
fonte: medição dos 5 vídeos do Depth Theory (2026-11-03) e o gerar_ae.py do formato
---

# Biblioteca de Cenas (bestiário, animação 2D)

10 tipos de cena, montados por `formatos/bestiario/gerar_ae.py`. Por baixo de todos, um **fundo** desenhado no After — `mar` (degradê azul-petróleo, raios de luz balançando, partículas subindo), `noite` (azul-noite com estrelas piscando), `grade` (grade técnica com cantoneiras), `escuro` — ou um **cenário gerado** (card `ilustracao` com `"fundo": true`). O fundo só troca quando a cena pede outro (fusão de 0,45 s); o primeiro é o `fundo_padrao` da ficha.

Tudo entra animado: elementos sobem 18 px e aparecem em 0,35 s; somem em 0,2 s; linhas (régua, sublinhado, risco, linha do tempo) se desenham. A criatura oscila sempre (sobe e desce ~9 px, gira ~1,4°).

| Código | Nome | Na tela | Quando usar | No Depth Theory |
|---|---|---|---|---|
| C1 | criatura em cena | a criatura recortada nadando (nada / entra / sobe / close / parado), opcional o "você" com sonar, rótulo em pílula, carimbo vermelho, frase-chave vermelha sublinhada | a base: o que a narração diz da criatura | o cachalote nadando, "IT KNOWS WHERE YOU ARE", "PREDATOR" |
| E1 | escala com régua | a criatura inteira, régua que se desenha embaixo, o tamanho em branco e a comparação em vermelho, a pessoa de 1,8 m na proporção | o capítulo do tamanho | "~16 M", "= 40 TONNES" |
| N1 | comparação em ícones | N ícones entrando um a um (o último pela metade) | peso, quantidade, "do tamanho de" | 6–7 elefantes, pessoas na gangorra |
| N2 | número grande | o número enorme, o rótulo embaixo, barra de nível opcional | o número que choca | "236 dB", "DAY 200", "0%" |
| L1 | suas opções | "YOUR OPTIONS" e os itens entrando quando ditos, riscados quando derrubados, veredito vermelho | o "what would you actually do?" | "1. SWIM AWAY … 5. HOPE IT SWALLOWS YOU" |
| D1 | documento | papel claro torto subindo: fonte em vermelho, título em serifa, a gravura antiga dentro (ou linhas de texto) | fonte antiga, artigo, relato registrado | artigo da Current Biology, "OFFICIAL COMPLAINT", capa de Moby-Dick |
| T1 | linha do tempo | linha que se desenha e os anos entrando com a legenda; destaque em vermelho | sequência de avistamentos/datas | 1925 · 1981 · 2003 |
| R1 | filmagem real | foto/vídeo como foto impressa torta (ou cheio), rótulo embaixo | o animal/lugar/objeto real | baleia saltando, urso na praia |
| F1 | frase | 2–8 palavras em maiúsculas, branca ou vermelha sublinhada | pergunta, virada, gancho | "WHAT DOES IT EAT?", "IF IT DECIDED YOU WERE A PROBLEM…" |
| S1 | lado a lado | divisória que se desenha, uma imagem de cada lado com o rótulo em cima | lenda × realidade, você × ela | "HUMPBACK: FILTERS / SPERM WHALE: ?" |

Título do capítulo: o nome em maiúsculas grandes à esquerda (2 linhas), sublinhado vermelho e a criatura do elenco nadando à direita.

Ainda não tem (a fazer se fizer falta): mapa animado (Antártida, Pangeia), pizza, raio-X do animal, velocímetro "você × ela", contador que sobe.
