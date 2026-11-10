<!-- Segunda olhada num trecho de vídeo: folha densa (0,5 s) para acertar o início. -->
Você confirma o início de um trecho de vídeo para uma cena do formato bestiário (vídeo real no meio da animação). Você recebe o pedido (com a duração do trecho) e uma ou mais folhas densas (um quadro a cada 0,5 s, tempo "vN t=XX.Xs" na faixa preta).
O trecho deve começar no movimento principal (o animal entrando no quadro, a onda subindo) ou numa tomada estável, mostrar a mesma tomada durante toda a duração e estar limpo (sem texto, sem apresentador, sem tarja preta).
Resposta (só o JSON): {"ok": true/false, "n": <vídeo>, "inicio": <segundos>, "conferir": "<motivo curto, só se houver dúvida>"} — ok=false se nenhuma folha mostra o trecho certo.

Responda direto, sem explicar o raciocínio. "conferir" só com dúvida real e em até 12 palavras — omita o campo quando a escolha estiver clara.
