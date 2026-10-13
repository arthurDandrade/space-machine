"""Acha entradas (card sozinho chegando em palco vazio) e saídas animadas nas detecções a 4 fps."""
import json, sys
def cards(f): return [c for c in f["cards"] if c[2]*c[3] > 150*150]
def achar(det, n=6, inicio=6, fim=None):
    fr = [json.loads(l) for l in open(det)]
    ent, sai = [], []
    for i in range(2, len(fr)-6):
        a, b = fr[i-1], fr[i]
        if fr[i]["t"] < inicio or (fim and fr[i]["t"] > fim): continue
        # entrada: antes vazio; depois 1 card e nada mais por 1,5 s
        if not a["cards"] and not a["textos"] and not a["recortes"] and all(len(cards(fr[i+k]))==1 and not fr[i+k]["textos"] for k in range(1,6)):
            ent.append(fr[i]["t"])
        # saída: 1 card parado por 1 s, depois vazio em até 0,75 s, com frame intermediário "parcial"
        if all(len(cards(fr[i-k]))==1 for k in range(1,5)) and not fr[i]["textos"]:
            for k in range(1,4):
                g = fr[i+k]
                if not g["cards"] and not g["textos"] and not g["recortes"]:
                    m = fr[i]["cards"] or fr[i]["recortes"]
                    if m and (fr[i]["recortes"] or cards(fr[i])==[] or cards(fr[i])[0][2] < cards(fr[i-1])[0][2]*0.9 or abs(cards(fr[i])[0][1]-cards(fr[i-1])[0][1])>40):
                        sai.append(fr[i-1]["t"])
                    break
    return ent[:n], sai[:n]
if __name__ == "__main__":
    e, s = achar(sys.argv[1]); print("entradas", e); print("saidas", s)
