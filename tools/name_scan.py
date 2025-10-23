import os
c=[]
for dp,ds,fs in os.walk('.'):
    for f in fs:
        if '-' in f or (f.endswith('.py') and any(c.isupper() for c in f)):
            c.append(os.path.join(dp,f))
for p in sorted(set(c)):
    print(p)
