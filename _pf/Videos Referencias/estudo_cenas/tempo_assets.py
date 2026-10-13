import json, sys, numpy as np
def iou(a,b):
    x0,y0=max(a[0],b[0]),max(a[1],b[1]); x1,y1=min(a[0]+a[2],b[0]+b[2]),min(a[1]+a[3],b[1]+b[3])
    i=max(0,x1-x0)*max(0,y1-y0); return i/float(a[2]*a[3]+b[2]*b[3]-i+1e-9)
def trilhas(fr, fps=4):
    vivas, fim = [], []
    for k,f in enumerate(fr):
        cs=[c for c in f['cards'] if c[2]*c[3]>150*150 and c[1]>30]
        novas=[]
        for c in cs:
            m=max(vivas, key=lambda t: iou(t['box'],c), default=None)
            if m and iou(m['box'],c)>0.5 and m not in novas:
                m['box']=c; m['n']+=1; novas.append(m)
            else:
                novas.append({'box':c,'n':1,'k0':k})
        for t in vivas:
            if t not in novas: fim.append(t)
        vivas=novas
    fim+=vivas
    return [t['n']/fps for t in fim if t['n']>=2]   # ignora flashes de 1 frame (transição)
for nome in sys.argv[1:]:
    fr=[json.loads(l) for l in open(f'det/{nome}.jsonl')]
    d=np.array(trilhas(fr))
    print(f'{nome:10s} assets={len(d):4d}  tempo na tela: p10={np.percentile(d,10):.1f}s  p25={np.percentile(d,25):.1f}  mediana={np.median(d):.1f}  p75={np.percentile(d,75):.1f}  <1,5s: {100*(d<1.5).mean():.0f}%')
