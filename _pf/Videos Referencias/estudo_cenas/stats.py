import json, numpy as np, collections
def estavel(fr):
    out=[]
    for i in range(1,len(fr)-1):
        a,b,c=fr[i-1],fr[i],fr[i+1]
        if len(a['cards'])==len(b['cards'])==len(c['cards']) and all(abs(p[k]-q[k])<40 for p,q in zip(sorted(a['cards']),sorted(b['cards'])) for k in range(4)):
            out.append(b)
    return out
tot=collections.Counter(); singles=[]; pares=[]; trios=[]; sobre=0; ncard=0; txt_com=collections.Counter(); rec=0
import sys
VS=[int(x) for x in sys.argv[1:]] or [1,2,3,4]
for v in VS:
    fr=[json.loads(l) for l in open(f'det/v{v}.jsonl')]
    for f in estavel(fr):
        cs=[c for c in f['cards'] if c[2]*c[3]>120*120 and c[1]>40]   # ignora barra/título
        n=len(cs); tot[min(n,4)]+=1
        if f['recortes']: rec+=1
        if n: txt_com[('texto' if f['textos'] else 'sem')]+=1
        if n==1: singles.append(cs[0])
        if n==2: pares.append(sorted(cs))
        if n==3: trios.append(sorted(cs))
s=sum(tot.values())
print('frames estáveis',s, {k:f'{100*v/s:.0f}%' for k,v in sorted(tot.items())})
print('com recorte solto', f'{100*rec/s:.0f}%', '| cards com texto preto ao lado', txt_com)
S=np.array(singles); w,h=S[:,2],S[:,3]; cx=S[:,0]+w/2; cy=S[:,1]+h/2; asp=w/h
q=lambda a:np.percentile(a,[10,25,50,75,90]).round(2)
print('\n1 CARD  n=',len(S)); print(' largura',q(w)); print(' altura',q(h)); print(' aspecto',q(asp))
print(' centro x',q(cx)); print(' centro y',q(cy))
print(' retrato %.0f%%  paisagem %.0f%%  quadrado %.0f%%'%(100*(asp<0.85).mean(),100*(asp>1.15).mean(),100*((asp>=0.85)&(asp<=1.15)).mean()))
print(' descentralizado (|cx-960|>200): %.0f%%'%(100*(abs(cx-960)>200).mean()))
print(' altura/1080 mediana %.2f'%np.median(h/1080))
P=np.array(pares)
h1,h2=P[:,0,3],P[:,1,3]; gap=P[:,1,0]-(P[:,0,0]+P[:,0,2])
print('\n2 CARDS n=',len(P)); print(' alturas',q((h1+h2)/2)); print(' razão alturas',q(np.minimum(h1,h2)/np.maximum(h1,h2)))
print(' gap',q(gap)); print(' sobrepostos (gap<0): %.0f%%'%(100*(gap<0).mean()))
yd=abs((P[:,0,1]+P[:,0,3]/2)-(P[:,1,1]+P[:,1,3]/2)); print(' diferença vertical centros',q(yd))
gx=(P[:,0,0]+P[:,1,0]+P[:,1,2])/2; print(' centro do grupo x',q(gx))
asp2=np.concatenate([P[:,0,2]/P[:,0,3],P[:,1,2]/P[:,1,3]]); print(' aspecto',q(asp2))
T=np.array(trios); print('\n3 CARDS n=',len(T)); print(' alturas',q(T[:,:,3].mean(1)))
