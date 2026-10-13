---
tags: [pro-football, edicao, after-effects]
status: editor automático funcionando (1º bloco montado em 2026-10-02)
pasta: motor/edicao_ae/
---

# Edição no After Effects

Voltar: [[00 - Pro Football (Índice)]] · Relacionado: [[Animação e Ritmo]] · [[Visual do Formato]]

O Claude monta cada bloco **automaticamente no After Effects 2026**, a partir do que a [[Como Buscar Assets|busca de assets]] entregou.

## Editor v2 (usa a Biblioteca de Cenas) ⭐ atual
- Entrada: `edicao/plano_edicao_<item>.json` — cada cena tem **estados** (a cena evolui), e cada estado tem `layout` + `cards` + `textos`/`rotulos`. Cards aceitam `sobre` (frases brancas em sequência), `acima` (nome acima), `legenda` (mini-legenda), `sticker` (logo PNG no canto), `png` (logo/recorte solto) e `arquivo` (usar uma alternativa dos candidatos).
- Layouts implementados: **A** (texto, com `cresce` = frase que se completa), **B** (1 card), **B4/B5** (card + rótulo lateral / rótulo em lista), **C1** (par), **C2** (cascata), **C4** (comparação com rótulos acima), **D1** (trio), **LOGOS** (PNGs lado a lado + texto abaixo). Ver códigos em [[Biblioteca de Cenas]].
- Rodar: `../../.venv/bin/python gerar_ae2.py <projeto> --item 01` → `montar_01_v2.jsx` no After → `render_01_v2.jsx`.
- Hierarquia no After: Null do estado (push-in) → Null "slot" de cada card (entrada/deriva/saída) → footage (máscara arredondada + sombra) e textos presos ao card.
- Pares e trios são cortados em **retrato/quadrado** (aspecto ≤ 1,0) para ficarem altos, como nas referências.
- Vídeo mais curto que o tempo de tela → time remap (segura o último frame).
- Também implementados (2026-10-02, testados em `edicao/plano_edicao_teste.json` → `previa_teste.mp4`):
  - **B6** troca no lugar: no card, `"troca": [{"asset": X, "t": ...}, ...]` — o quadro fica e o conteúdo troca por corte.
  - **D2** 1 grande + 2–3 pequenos empilhados (pequenos cortados em paisagem).
  - **D3** moldura: pessoa – objeto (maior, no centro) – pessoa.
  - **D4** esteira: cards alinhados a partir da esquerda, todos entram pela direita; o último pode ficar parcialmente fora da tela.
  - **E2** recorte (PNG) + card lado a lado.
  - **E3** recorte + bloco de texto (rótulo longo vira 2–3 linhas).
  - **A3** frase em 2 linhas: texto com modo `"2linhas"`.
  - Qualquer card aceita `"entra"`/`"sai"`: `"baixo"`, `"cima"`, `"esq"`, `"dir"`.
- Todas as famílias da [[Biblioteca de Cenas]] agora têm suporte no editor.

## Como funciona (editor v1 — histórico)
> [!warning] Seção do editor v1 (`gerar_ae.py` + `montar_modelo.jsx`), aposentado. O atual é o **v2** (acima): `editor_ae/editar_bloco.sh <bloco> NN [versão]` roda `gerar_ae2.py` → `montar_NN_v2.jsx` → `renderizar.jsx` → QA. (2026-10-13)

```
plano.json + manifesto.json + narração
        │  gerar_ae.py   (calcula layout, tempos, keyframes)
        ▼
edicao/montar_<item>.jsx  ──► After Effects (osascript DoScriptFile)
        ▼
edicao/bloco_<item>.aep   ──► renderizar.jsx (fila de render do After)
        ▼
edicao/previa_bloco_<item>.mp4
```
- Pasta do editor: `motor/edicao_ae/` (`gerar_ae.py`, `montar_modelo.jsx`, `renderizar.jsx`).
- Comandos:
  ```bash
  cd motor/edicao_ae
  ../../.venv/bin/python gerar_ae.py <projeto> --item 01
  osascript -e 'tell application "Adobe After Effects 2026" to DoScriptFile "<projeto>/edicao/montar_01.jsx"'
  ```
  O script grava `edicao/log_01.txt` (OK ou erro com a linha).
- Render: `edicao/render_01.jsx` (gerado com o caminho do .aep) → `previa_bloco_01.mp4`. ~2 min para 84 s.

## O que o script monta
- Comp 1920×1080, 60 fps, motion blur ligado (obturador 180°).
- **Fundo**: sólido `#F3F3F3` + "Textura papel" (Fractal Noise, Soft Light 14%) + "Vinheta" (máscara elíptica invertida, feather 650, 13%). Travados.
- **Narração** no tempo 0.
- **Um Null por cena** em (960,540), âncora 0 → push-in linear de +2,5%/s (máx. 115%). Tudo da cena é filho dele.
- **Cards**: footage + máscara de retângulo arredondado (raio 5% do lado menor; também recorta paisagem→quadrado em layouts de 2–3 cards) + Drop Shadow (50%, softness compensada pela escala) + entrada/deriva/saída por keyframes.
- **Textos**: Avenir Next Heavy; tamanho ajustado pela largura (sourceRectAtTime); Drop Shadow; fade + Gaussian Blur 8→0 em 0,18 s.
- **Título do item**: nome em 2 linhas no topo + PNG com scale pop de 0,27 s.

## Regras de montagem (decididas no 1º bloco)
- Elemento entra 0,2 s antes da palavra-gatilho; **o 1º elemento da cena entra quando a cena começa** (senão o palco fica vazio por segundos).
- Saída animada em cenas com 2+ cards e em ~1/3 das de 1 card; resto é corte seco. A saída termina 0,12 s depois do início da próxima cena (sobreposição).
- Card entra pela borda mais próxima (empate: de baixo).
- Asset pulado → a cena vira **texto solo em trechos** (ex.: "From there, he delivered" / "a sidearm pass" / "to Spencer Ware").

## Pegadinhas do After (scripting)
- `DoScript` via osascript **sempre devolve 0** → o script grava um log em arquivo (a preferência "Allow Scripts to Write Files" já está ligada).
- Fractal Noise: propriedades são planas; escala é `ADBE Fractal Noise-0010` (não "Transform > Scale").
- Não dá para mover camada travada: travar o fundo **depois** de `moveToEnd()`.
- Drop Shadow: opacidade vai de 0 a 255 (127,5 = 50%); o efeito roda no espaço da camada, então softness/distância são divididos pela escala.
- `aerender` não achou o template "H.264 - Match Render Settings - 15 Mbps" → renderizar pela fila de render dentro do After (`renderizar.jsx`).

## Fonte
Títulos e nomes: **Impact** maiúscula (`FONTE_MARCA` em `gerar_ae2.py`, ou `fonte_marca` no `canal.json`). Texto corrido: Avenir Next Heavy (`FONTE`). Ver [[Identidade Visual]].

## Pendências
- [ ] Confirmar a fonte com o Arthur.
- [ ] Juntar blocos num vídeo completo (sequência de comps + 8–10 s de tela vazia no fim).
- [ ] Saídas em direções opostas (hoje cards do mesmo lado saem pela mesma borda).
