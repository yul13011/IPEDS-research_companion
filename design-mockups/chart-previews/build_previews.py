"""Static presentation proposals; does not modify the application."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

OUT=Path(__file__).parent
result=json.loads((OUT/'source_result.json').read_text(encoding='utf-8'))
names=['Mount Holyoke College','Smith College']
series={n:sorted([r for r in result['rows'] if r['institution']==n],key=lambda r:r['observation_year']) for n in names}
assert all(len(v)==10 and all(r['status']=='ok' for r in v) for v in series.values())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13,'text.color':'#172B3A','axes.labelcolor':'#52616D','xtick.color':'#52616D','ytick.color':'#52616D','svg.fonttype':'none'})
blue='#2367A0';orange='#B96028';gray='#8A959F'
def canvas(k,subtitle):
    fig=plt.figure(figsize=(16,9),facecolor='white')
    fig.text(.07,.925,k,fontsize=11,color='#647583',weight='bold')
    fig.text(.07,.855,'Fall enrollment at Mount Holyoke and Smith',fontsize=28,weight='bold')
    fig.text(.07,.805,subtitle,fontsize=15,color='#52616D')
    fig.text(.07,.075,'Source: IPEDS · Fall Enrollment · EF2015A–EF2024A · Fall 2015–2024',fontsize=11,color='#52616D')
    fig.text(.07,.043,'Total enrollment includes undergraduate and graduate students. Latest release: 2024–25 provisional.',fontsize=10,color='#647583')
    return fig
def style(ax):
    ax.set_ylim(0,4000);ax.set_yticks([0,1000,2000,3000,4000]);ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
    ax.set_xticks(range(2015,2025));ax.set_xlim(2014.8,2024.2)
    ax.grid(axis='y',color='#E5E9ED',lw=.8);ax.set_axisbelow(True)
    for s in ['top','right','left']:ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#C6CED5');ax.tick_params(length=0,pad=10)
    ax.set_xlabel('Year',labelpad=14);ax.set_ylabel('Students',labelpad=14)
def line(ax,n,color,**kw):
    rr=series[n];ax.plot([r['observation_year'] for r in rr],[r['value'] for r in rr],color=color,lw=2.8,**kw)
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=150,facecolor='white')
    fig.savefig(OUT/(name+'.svg'),facecolor='white');plt.close(fig)

fig=canvas('01 / CLEAN COMPARISON','Two series · consistent scale · every year labeled · compact legend')
ax=fig.add_axes([.09,.22,.84,.48]);style(ax)
line(ax,names[0],blue,marker='o',ms=6,label=names[0]);line(ax,names[1],orange,marker='s',ms=5.5,ls='--',label=names[1])
ax.legend(loc='lower left',bbox_to_anchor=(0,1.04),frameon=False,ncol=2,fontsize=13,handlelength=3)
save(fig,'01-clean-comparison')

fig=canvas('02 / FOCUS AND DIRECT LABELS','One institution emphasized · peer muted · latest values labeled directly')
ax=fig.add_axes([.09,.22,.65,.49]);style(ax)
line(ax,names[1],gray,ls='--');line(ax,names[0],blue,marker='o',ms=5)
for n,c in [(names[0],blue),(names[1],gray)]:
    v=series[n][-1]['value'];ax.scatter([2024],[v],s=55,color=c,zorder=4)
    ax.annotate(f'{n}\n{v:,.0f} students',xy=(2024,v),xytext=(18,0),textcoords='offset points',va='center',fontsize=13,color=c,weight='bold',annotation_clip=False)
save(fig,'02-focus-direct-labels')

fig=canvas('03 / MATCHED PANELS','Separate panels · shared scale · endpoints labeled · suitable for two-column slides')
for i,(n,c) in enumerate(zip(names,[blue,orange])):
    ax=fig.add_axes([.09+i*.46,.23,.37,.44]);style(ax)
    ax.set_title(n,loc='left',fontsize=17,weight='bold',pad=25)
    ax.tick_params(axis='x',labelsize=10,pad=9)
    line(ax,n,c,marker='o',ms=4.5)
    for r in [series[n][0],series[n][-1]]:
        ax.annotate(f"{r['value']:,.0f}",(r['observation_year'],r['value']),xytext=(0,12),textcoords='offset points',ha='center',color=c,fontsize=12,weight='bold')
save(fig,'03-matched-panels')
print(json.dumps({n:[r['value'] for r in rr] for n,rr in series.items()}))
