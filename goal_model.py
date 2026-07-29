from math import exp, factorial

def pois(k,l):return exp(-l)*l**k/factorial(k)
def distribution(lh,la,n=8):
    d=[[pois(i,lh)*pois(j,la) for j in range(n+1)] for i in range(n+1)]
    total=sum(map(sum,d)); return d,total
def fit_lambdas(probs):
    # Fit independent-Poisson score distribution to no-vig home/draw/away probabilities.
    best=None
    for a in range(20,421,5):
      lh=a/100
      for b in range(20,421,5):
        la=b/100;d,_=distribution(lh,la,8)
        h=sum(d[i][j] for i in range(9) for j in range(9) if i>j)
        dr=sum(d[i][i] for i in range(9)); aw=sum(d[i][j] for i in range(9) for j in range(9) if i<j)
        err=(h-probs[0])**2+(dr-probs[1])**2+(aw-probs[2])**2
        if best is None or err<best[0]:best=(err,lh,la,d)
    return best[1],best[2],best[3]
def summary(probs):
    lh,la,d=fit_lambdas(probs)
    scores=sorted(((d[i][j],f'{i}-{j}') for i in range(6) for j in range(6)),reverse=True)[:3]
    totals=[]
    for k in range(7): totals.append(sum(d[i][j] for i in range(9) for j in range(9) if i+j==k))
    totals.append(max(0,1-sum(totals)))
    return {'lambda_home':round(lh,2),'lambda_away':round(la,2),'scores':[(x[1],round(x[0],4)) for x in scores],'totals':totals}
