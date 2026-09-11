from collections import defaultdict
from django.utils import timezone
from .models import PPA, Unit

def quarter_for_date(d): return ((d.month-1)//3)+1 if d else None

def forecast_projects(year=None):
    """Simple least-squares trend on cumulative project starts by quarter, no external ML dependency."""
    year=year or timezone.localdate().year
    results=[]
    for unit in Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE):
        starts=[0,0,0,0]
        for p in PPA.objects.filter(ppa_type=PPA.PROJECT,unit=unit,start_date__year=year):
            q=quarter_for_date(p.start_date)
            if q: starts[q-1]+=1
        cumulative=[]; running=0
        for n in starts: running+=n; cumulative.append(running)
        xs=[1,2,3,4]
        if sum(starts)==0:
            slope=0.0; intercept=0.0
        else:
            xm=sum(xs)/4; ym=sum(cumulative)/4
            denom=sum((x-xm)**2 for x in xs) or 1
            slope=sum((x-xm)*(y-ym) for x,y in zip(xs,cumulative))/denom
            intercept=ym-slope*xm
        current_q=((timezone.localdate().month-1)//3)+1 if year==timezone.localdate().year else 4
        next_q=min(4,current_q+1)
        q_forecast=max(cumulative[current_q-1] if cumulative else 0, round(intercept+slope*next_q))
        year_forecast=max(cumulative[-1], round(intercept+slope*4))
        results.append({'unit':unit,'actual':cumulative[current_q-1] if cumulative else 0,'quarter_forecast':q_forecast,'year_forecast':year_forecast,'starts':starts})
    results.sort(key=lambda x:(-x['year_forecast'],x['unit'].name))
    return results
