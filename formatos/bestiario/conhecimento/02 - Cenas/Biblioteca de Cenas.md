---
tags: [bestiario, cenas]
---

# Biblioteca de Cenas (bestiário)

7 tipos de cena, montados por `formatos/bestiario/gerar_ae.py`. Tudo sobre fundo preto; cada imagem entra e sai em fusão de ~0,45 s e anda devagar (zoom de ~1,2%/s, no máximo 12%, alternando aproximar e afastar).

| Código | Nome | Na tela | Quando usar |
|---|---|---|---|
| P1 | imagem plena | ilustração, foto ou vídeo enchendo a tela | a base: cada ideia da narração |
| P2 | plena + legenda | P1 + nome/número/data/lugar embaixo, branco em maiúsculas | o número que importa ("40 m", "1752", "Norway") |
| R1 | gravura no escuro | gravura antiga inteira no meio, traço claro sobre preto | a lenda como foi desenhada na época |
| D1 | lenda × realidade | duas imagens lado a lado, rótulo vermelho em cima de cada | a virada: o desenho antigo × o animal real |
| E1 | escala | a criatura inteira à direita, uma pessoa de 1,8 m à esquerda na proporção, o tamanho em vermelho | uma vez por vídeo, no capítulo do tamanho |
| T1 | frase | 2–7 palavras em serifa branca (ou vermelha) no meio | a frase de impacto, o gancho |
| Q1 | citação antiga | a citação real em itálico, a fonte em vermelho embaixo | "Its back is a mile and a half around" — Pontoppidan, 1752 |

Título do capítulo: o nome em serifa grande sobre a imagem do título apagada (40%).

Gravura e ilustração entram em modo **tela** (o preto da imagem some no fundo, sem borda de retângulo). Foto vira preto e branco no Python; vídeo, no After (Tint + contraste).
