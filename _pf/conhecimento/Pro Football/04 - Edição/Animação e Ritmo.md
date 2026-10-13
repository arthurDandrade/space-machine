---
tags: [pro-football, edicao, animacao, timing]
fonte: medições em 60 fps dos vídeos de referência (2026-10-02)
---

# Animação e Ritmo

Voltar: [[00 - Pro Football (Índice)]] · Relacionado: [[Visual do Formato]] · [[Edição no After Effects]]

Todo elemento tem 3 fases: **ENTRADA → FLUTUAÇÃO → SAÍDA**.

## Entrada de card (medido a 60 fps — corrigido em 2026-10-03)
- **Slide de fora da tela** até a posição final, vindo da borda mais próxima (de baixo é o mais comum).
- **Ease-out cúbico de ~0,95 s** (do lado de fora até parar): visível, faz 50% do trajeto em 0,13 s, 90% em 0,38 s e 98% em 0,54 s — rápido no começo mas **sem tranco**, e assenta suavemente (é isso que parece "continuar deslizando").
- No After: 1º keyframe com velocidade de saída 3·D/T e influência 33%; 2º keyframe com velocidade 0 e influência 67%.
- Opacidade 0→100% nos primeiros ~0,2 s; motion blur ligado.
- Cada card entra **na sua palavra-gatilho**.

## Entrada de PNG / título
**Scale pop** de ~0% a 100% em ~0,25–0,27 s, ease-out forte, sem overshoot. O texto do título faz fade de 0,17 s junto.

## Entrada de texto
**Fade 0→100% + desfoque ~8 px→0 em ~0,17–0,2 s** (10–12 frames a 60 fps). Sem movimento, sem escala, frase inteira de uma vez.

## Flutuação
- A **cena inteira faz push-in lento e linear**, escalando a partir do **centro da tela** (não de cada card).
- **+1,4% a +4,6% por segundo** (típico ~2,5%/s) → cada cena vai de 100% a ~108–115%.
- ⚠️ O zoom é **limitado por cena**: nenhum elemento pode passar de 50 px da borda (texto perto da borda = zoom menor).

## Saída
| Tipo | Ramen | Chocolate | Luxury | Sugars |
|---|---|---|---|---|
| Corte seco | 85% | 59% | 64% | 68% |
| Saída animada | 15% | 41% | 36% | 32% |

- **Corte seco sempre**: texto solo → próxima cena; título → 1ª cena; troca de frase de texto (some em 1 frame, ~5 frames vazios, próxima faz fade).
- **Saída animada** (mais em cenas de 2+ cards): cards **aceleram para fora** pela borda mais próxima, muitas vezes em direções opostas: **ease-in quadrático de ~0,8 s** (começa parado; ~0,4 s visível saindo), com motion blur. A próxima cena **começa a entrar antes** (~0,1–0,25 s de sobreposição).
- **Texto junto de card que sai animado** (rótulo, texto do E3, nome acima): sai **na mesma janela** dos cards (apaga em 0,8 s). Sumir num corte enquanto o card ainda sai pareceu bug ao Arthur (positions bloco 01, 2026-10-12).

## Palco vazio entre cenas
Mediana **0,1–0,2 s**. Nunca pausa longa vazia (só no fim do vídeo).

## Sincronia com a narração
1. Elemento entra **na palavra que ilustra**, com antecipação de ~0,05–0,3 s.
2. **Texto solo** = narração em trechos de 2–6 palavras; cada trecho aparece na primeira palavra e fica até o próximo.
3. Texto sobre card / rótulo = só a palavra-chave (data, número, nome) no momento em que é dita.
4. Troca de cena acompanha a troca de ideia.
5. Algo novo a cada **1–2 s**.
6. Elementos **se somam** dentro da cena; tudo sai junto.

> [!note] Diferença para o formato Simple Paint
> O Simple Paint (skill `banco-de-edicao`) é **só corte seco, nada se move**. Este formato é o oposto em movimento. Em comum: elementos se somam, entram antes da palavra, áudio só narração.
