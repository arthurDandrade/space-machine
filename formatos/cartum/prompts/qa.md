<!-- Correção automática depois de um QA reprovado (rodar.py _corrigir_qa). -->
# Correção depois do QA
O tópico já foi desenhado pelo compositor e o controle de qualidade (qa_bloco.py) reprovou. Cada FALHA vem com os tempos (↳) em que o defeito aparece. Corrija só o que as FALHAS pedem, no cenas.json, mexendo o mínimo possível:
- **Palco vazio** (só o fundo e o cabeçalho na tela por mais de 0,5 s no meio do tópico): o 1º card do estado entra mais cedo (gatilho na primeira palavra da fala) ou o estado começa numa palavra anterior.
- **Texto pouco tempo na tela** (menos de 0,7 s): mova o gatilho do `acima`/`legenda`/`balao` para uma palavra anterior, para o texto ficar pelo menos 1 s.
- **Origem dos assets** (banco com marca d'água ou assunto proibido no tema): troque aquele card por um card novo, sem "id", com a mesma descrição; ele será buscado de novo.
- Mantenha os "id" dos cards que continuam (eles já têm arquivo); card novo vem sem "id" e será buscado (desenho novo é gerado de novo; com "elenco", não).
Responda SÓ com o JSON do cenas.json completo.
