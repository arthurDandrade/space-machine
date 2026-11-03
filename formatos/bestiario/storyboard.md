# Regras do storyboard (formato bestiário)

Lidas pelo orquestrador (`rodar._sistema_storyboard`), junto com as regras do tema do canal. O `storyboard.py` mede as que dá. As metas são PROVISÓRIAS (2026-11-03) até o vídeo piloto ser medido.

## Os 7 tipos de cena e como escrever cada um no cenas.json
- **P1 imagem plena**: `{"layout": "P1", "fala": "...", "cards": [{"gatilho": "...", "tipo": "ilustracao"|"foto"|"video", "descricao": "...", "buscas": [...]}]}`. A imagem enche a tela e anda devagar. Trocas no mesmo lugar: `"troca": [{"gatilho": "...", "tipo": ..., ...}]` (fusão de uma para a outra).
- **P2 plena + legenda**: P1 com `"legenda": ["texto", "gatilho"]` no card: nome, número, data ou lugar, embaixo, em maiúsculas.
- **R1 gravura no escuro**: `{"layout": "R1", "cards": [{"tipo": "gravura", ...}]}`. A gravura antiga, inteira, no meio da tela preta (o papel é invertido: traço claro sobre preto).
- **D1 lenda × realidade**: dois cards lado a lado com `"acima": ["LEGEND", "gatilho"]` / `"acima": ["REALITY", "gatilho"]` (ou o nome de cada um). Em geral a gravura/ilustração da lenda e a foto do animal real. Gatilhos diferentes: o 2º card entra quando a fala chega nele.
- **E1 escala**: um card `"tipo": "ilustracao"` com a criatura INTEIRA de lado e `"escala": {"tamanho_m": 40, "medida": "comprimento"|"altura", "pessoa_rotulo": "you"}`; o tamanho vai em `"rotulos": [["40 m", "forty"]]`. O editor desenha uma pessoa de 1,8 m ao lado, na proporção certa. Peça a criatura sem nada em volta ("full body, side view, isolated, nothing else in the frame").
- **T1 frase**: `{"layout": "T1", "fala": "...", "textos": [["texto", "gatilho"]]}`. Frase curta (2–7 palavras) em serifa branca no meio. `["texto", "gatilho", "vermelho"]` para a frase em vermelho (uma por bloco, no máximo). Vários textos no mesmo estado trocam um pelo outro.
- **Q1 citação antiga**: `"textos": [["a citação", "gatilho"], ["Olaus Magnus, 1555", "gatilho"]]`: a frase REAL de uma fonte antiga, em itálico, e a fonte embaixo em vermelho. Só citação que está no roteiro.
- Título do capítulo (o card do começo do bloco): `"titulo": {"tipo": "ilustracao", "descricao": "...", "buscas": ["<pedido>"]}` ou `{"tipo": "gravura", ...}` ou `{"reusar": "<id>"}` para usar uma imagem que já existe. O nome vai em serifa grande sobre a imagem apagada. Cold open: `"sem_titulo": true`.

## Regras (o `storyboard.py` confere as que dá para medir)
1. **Cada imagem fica 3–7 s na tela** e nunca menos de 1,8 s. Troque de imagem quando a ideia muda; frase seguida do mesmo assunto continua na mesma imagem (ou numa `troca` dela).
2. **≥ 4 tipos de cena por bloco**, cada um no máximo 4 vezes. P1 é a base; R1 e D1 dão o "documento antigo"; E1 uma vez por vídeo, no capítulo do tamanho; T1 e Q1 pontuam.
3. **Texto solo (T1 + Q1) em 5–22% do tempo.** Texto sobre imagem só na legenda do P2 (nome, número, data, lugar).
4. **≥ 25% das cenas evoluem** (2–3 estados: P1 → P2 com a legenda, R1 → D1 com a realidade, P1 → T1).
5. **Ilustração no máximo 6 por bloco** (cada uma gera 3 opções pagas). Prefira gravura antiga quando ela existe (Commons tem milhares: Olaus Magnus, Gessner, Aldrovandi, bestiários medievais) e ilustração para o que a gravura não mostra: o ponto de vista em segunda pessoa ("you are on the deck and the water rises"), a escala, a cena que o roteiro descreve.
6. **Nunca ilustração de pessoa real ou acontecimento real.** O naufrágio com nome e data, o autor da crônica, o avistamento registrado: gravura de época ou foto histórica. Pessoa genérica sem rosto pode ("a lone sailor seen from behind").
7. **A mesma criatura em todo o vídeo**: copie a ficha da criatura (seção Gravuras e Ilustrações) igual em cada pedido de ilustração dela.
8. **O real é foto ou vídeo**: o animal que inspirou a lenda (lula-gigante, regaleco, baleia, lobo), o mar, a floresta, o fóssil. Vídeo só do que existe aos montes em banco livre; o resto é foto.
9. **Gatilho = palavra como está na transcrição** (o Whisper erra: use a palavra errada no gatilho e o texto certo na tela).
10. **YouTube não é fonte** (2026-10-11): nada de trecho de documentário, filme, série ou jogo. Franquia nenhuma (Harry Potter, Witcher, D&D...): só folclore, fontes antigas e ciência.
