"""Test evidence and original figures for the local topology experiments."""
import json
import math
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.plot-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import numpy as np
from topology import triangle_chain,skeleton,edges
BLUE,ORANGE,TEAL,INK='#236783','#d36c37','#348b72','#1b2935'


def saved():return json.loads((ROOT/'topology_results.json').read_text(encoding='utf-8'))


def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=130,bbox_inches='tight');plt.close(fig)


def constructions():
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    ax=axes[0,0];ax.axis('off');ax.set_title('A finite lifting problem')
    for label,xy in [('D: 4 vertices',(.2,.85)),('B: 3 vertices',(.8,.85)),
                     ('C: 3 vertices',(.2,.2)),('A: 2 vertices',(.8,.2))]:
        ax.text(*xy,label,ha='center',va='center',bbox={'boxstyle':'round,pad=.45','fc':'#e7eef0','ec':'none'})
    for start,end,label in [((.37,.85),(.61,.85),'pB'),((.2,.73),(.2,.31),'pC'),
                             ((.8,.73),(.8,.31),'g'),((.37,.2),(.61,.2),'f')]:
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':INK})
        ax.text((start[0]+end[0])/2+.025,(start[1]+end[1])/2+.04,label)
    ax.text(.5,.53,'g ∘ pB = f ∘ pC',ha='center',color=BLUE)
    ax.text(.5,0,'No direct C → B lift; refinement supplies one.',ha='center',fontsize=8)
    ax=axes[0,1]
    verts=np.array([[0,0],[1,0],[.5,.85]])
    ax.add_patch(Polygon(verts,facecolor='#e8f0ec',edgecolor=INK))
    point=.4*verts[1]+.6*verts[2];ax.scatter(*point,c=ORANGE,s=45,zorder=3)
    ax.plot(verts[[1,2],0],verts[[1,2],1],color=BLUE,lw=3)
    for i,v in enumerate(verts):ax.text(v[0],v[1]-.08 if i<2 else v[1]+.05,str(i),ha='center')
    ax.text(.45,-.25,'D₀(0.4,0.6) = (0,0.4,0.6)',ha='center',fontsize=9)
    ax.text(.45,-.4,'Both descriptions locate the same point.',ha='center',fontsize=8)
    ax.set(title='Face gluing: equality of locations',xlim=(-.15,1.15),ylim=(-.45,1));ax.set_aspect('equal');ax.axis('off')
    ax=axes[0,2];x=np.linspace(0,1,150);X,Y=np.meshgrid(x,x)
    im=ax.imshow(np.maximum(X,Y),origin='lower',extent=(0,1,0,1),cmap='Blues',vmin=0,vmax=1,aspect='auto')
    ax.contour(X,Y,np.maximum(X,Y),levels=[.25,.5,.75],colors=INK,linewidths=.6)
    ax.set(title='Cube connection: γ(x,y) = max(x,y)',xlabel='x',ylabel='y')
    fig.colorbar(im,ax=ax,shrink=.7,label='Collapsed coordinate')
    ax=axes[1,0];ax.set_title('Filling changes holes, preserves links');ax.axis('off')
    coords=np.array([[0,0],[.5,.65],[1,0],[1.5,.65],[2,0],[2.5,.65],[3,0],[3.5,.65],[4,0]])
    for filled,offset in [(False,1.4),(True,0)]:
        points=coords+[0,offset];K=triangle_chain(filled)
        if filled:
            for tri in K:
                if len(tri)==3:ax.add_patch(Polygon(points[list(tri)],facecolor='#cae4d8',edgecolor='none'))
        for i,j in edges(skeleton(K),False):ax.plot(points[[i,j],0],points[[i,j],1],color=BLUE,lw=1.4)
        ax.scatter(points[:,0],points[:,1],color=INK,s=16)
        ax.text(2,offset-.35,'4 independent loops' if not filled else '0 unfilled loops',ha='center',fontsize=9)
    ax.set(xlim=(-.15,4.15),ylim=(-.55,2.2))
    ax=axes[1,1];ax.set_title('Same totals; different expected change');ax.axis('off')
    examples=[([0,0,1,0,0,1],1,'A: block 1 drift −17/240'),([0,1,0,0,1,0],0,'B: block 1 drift +17/240')]
    for state,y,label in examples:
        for left in (-.4,2.6):ax.add_patch(Rectangle((left,y-.24),2.8,.48,facecolor='#edf1f2',edgecolor='none'))
        ax.plot(range(6),[y]*6,color='#8999a1',lw=1)
        ax.scatter(range(6),[y]*6,c=[BLUE if v==0 else ORANGE for v in state],s=95,zorder=3)
        ax.text(2.5,y-.45,label,ha='center',fontsize=9)
    ax.text(2.5,1.55,'Each block has two blue and one orange.',ha='center',fontsize=8)
    ax.set(xlim=(-.6,5.6),ylim=(-.6,1.7))
    ax=axes[1,2];ax.set_title('Nerve: composition and identity');ax.axis('off')
    for y,labels in [(1,['1','2']),(0,['1','0 = identity','2'])]:
        xs=np.linspace(.1,.9,len(labels)+1)
        for px in xs:ax.text(px,y,'•',ha='center',va='center',fontsize=20,color=BLUE)
        for a,b,label in zip(xs,xs[1:],labels):
            ax.annotate('',xy=(b-.025,y),xytext=(a+.025,y),arrowprops={'arrowstyle':'->','color':INK})
            ax.text((a+b)/2,y+.16,label,ha='center',fontsize=8)
    ax.text(.5,.57,'1 + 2 = 0 (mod 3)',ha='center',color=ORANGE)
    ax.text(.5,-.37,'One object, displayed repeatedly along a chain.',ha='center',fontsize=8)
    ax.set(xlim=(0,1),ylim=(-.55,1.5))
    fig.suptitle('Turning the slides into verifiable constructions',fontsize=16)
    save(fig,'topology_checks')


def model_results():
    d=saved();fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    cases=[r for r in d['sims']['cases'] if r['initiative']==0]
    ax=axes[0]
    for name,color,offset in [('Menger contacts',BLUE,-.19),('Transitive closure contacts',ORANGE,.19)]:
        rows=[r for r in cases if r['network']==name];xs=np.arange(3)+offset
        y=np.array([r['first_consensus_fraction']*100 for r in rows]);ci=np.array([r['wilson95'] for r in rows]).T*100
        ax.bar(xs,y,.36,color=color,label='Menger: 24 links' if name=='Menger contacts' else 'Closure: 190 links')
        ax.errorbar(xs,y,yerr=np.maximum(0,np.vstack((y-ci[0],ci[1]-y))),fmt='none',color=INK,capsize=3,lw=.8)
        ax.scatter(xs,[r['endpoint_fraction']*100 for r in rows],s=100,marker='_',color=INK)
    ax.set_xticks(range(3),['Ordinary','Corner\nopposes','Edge\nopposes'])
    ax.set(title='More contacts changes the outcome',ylabel='First consensus (%)',ylim=(0,100));ax.legend(fontsize=8)
    ax=axes[1]
    for offset,initiative,color in [(-.18,0,BLUE),(.18,.02,ORANGE)]:
        rows=[r for r in d['sims']['cases'] if r['network'] in ('Triangle wireframe','Filled triangles') and r['initiative']==initiative]
        ax.bar(np.arange(2)+offset,[r['first_consensus_fraction']*100 for r in rows],.34,color=color,label=f'Initiative {initiative}')
        ax.scatter(np.arange(2)+offset,[r['endpoint_fraction']*100 for r in rows],s=100,marker='_',color=INK)
    ax.set_xticks([0,1],['Wireframe','Filled faces']);ax.set(title='Same contacts: exact paired equality',ylabel='First consensus (%)',ylim=(0,105));ax.legend(fontsize=8)
    ax.text(.5,.07,'All 320 matched pairs agree\non every recorded outcome.',transform=ax.transAxes,ha='center',fontsize=9)
    ax=axes[2]
    for name,color in [('Menger contacts',BLUE),('Transitive closure contacts',ORANGE)]:
        r=next(r for r in cases if r['network']==name and r['policy']=='ordinary')
        values=np.array(r['copy_credit_by_seat']);values=values/values.sum()*100
        ax.plot(range(20),values,'o-',color=color,ms=3,lw=.8,label='Menger' if name=='Menger contacts' else 'Complete graph')
    ax.set(title='Direct copying credit by position',xlabel='Seat index',ylabel='Share of copying credit (%)');ax.legend(fontsize=8)
    fig.suptitle('2,560 additional SIMS runs · black marks show unanimity at 120 seconds',fontsize=14)
    save(fig,'topology_sims')


def build_figures():constructions();model_results()


def html_section():
    d=saved();m=d['mathematics'];s=d['sims']
    counts=sum(m[k]['equalities_checked'] for k in ('simplicial_identities','category_nerve','cubical_relations'))
    def find(network,policy='ordinary',role='baseline'):
        return next(r for r in s['cases'] if r['network']==network and r['policy']==policy and r['role']==role and r['initiative']==0)
    def table(initiative):
        rows=''.join(f"<tr><td>{r['network']}</td><td>{r['policy']} / {r['role']}</td><td>{r['first_consensus_fraction']:.2%}</td><td>{r['endpoint_fraction']:.2%}</td><td>{r['mean_capped_seconds']:.1f}</td><td>{r['mean_switches']:.1f}</td></tr>" for r in s['cases'] if r['initiative']==initiative)
        return '<div class="scroll"><table><tr><th>Contacts</th><th>Rule / seat</th><th>First agreement</th><th>At 120 s</th><th>Capped seconds</th><th>Switches</th></tr>'+rows+'</table></div>'
    return f'''<section id="topology"><h2>Batch 4 · use topology to test the model</h2>
<p>Your slides become executable checks: graph projections and lifting, simplicial gluing, category nerves, cube collapses, and controls for how those constructions affect SIMS. This batch was developed and tested locally.</p>
<p><strong>{counts:,} finite algebraic equalities pass</strong>, alongside graph, homology, and behavioral checks. The new SIMS experiment contains {s['new_rounds']:,} runs with matched starting states and randomized condition order.</p>
<figure><img src="figures/topology_checks.png" alt="Finite lifting diagram, face gluing, maximum cube connection, filled versus wireframe triangles, aggregation counterexample, and category nerve"><figcaption>These are concrete finite constructions. The tested degrees, parameters, and negative controls are recorded in the methods.</figcaption></figure>
<h3>Test 1 · does a valid graph projection preserve behavior?</h3><p>The Menger parent maps pass the connected-epimorphism checks: 400 vertices map onto 20, then onto 1. A separate six-SIM path exposes a limit of aggregation: two arrangements have one orange SIM in each three-SIM block, yet the first block's expected next change is −17/240 in one arrangement and +17/240 in the other. Both blocks look blue under majority reporting even though neither microscopic state is unanimous.</p>
<p>This is an exact one-update calculation, conditional on an active uniformly chosen seat and the model's 15% refusal probability. Matching group totals does not preserve the future dynamics by itself. Who occupies which contact position still matters, even with identical SIM behavior.</p>
<h3>Test 2 · does adding filled faces change pairwise coordination?</h3><p>Four connected triangle outlines have four independent unfilled loops. Filling the triangles removes those loops while preserving all nine vertices and twelve pairwise links. The pairwise SIMS model produces <strong>identical recorded outcomes in all {s['exact_wireframe_filled_matched_pairs']} matched pairs</strong>, including initiative sensitivity. A behavioral effect from group faces would require a rule that actually reads those faces.</p>
<h3>Test 3 · what happens if transitivity adds contacts?</h3><p>The finite Menger graph's adjacency is not transitive. Its transitive closure connects all 20 positions, increasing links from 24 to 190. Ordinary first agreement rises from <strong>{find('Menger contacts')['first_consensus_fraction']:.2%}</strong> to <strong>{find('Transitive closure contacts')['first_consensus_fraction']:.2%}</strong> in this matched sample. With the corner position actively opposing, first agreement instead falls from <strong>{find('Menger contacts','oppose','corner')['first_consensus_fraction']:.2%}</strong> to <strong>{find('Transitive closure contacts','oppose','corner')['first_consensus_fraction']:.2%}</strong>; lasting agreement remains rare.</p>
<figure><img src="figures/topology_sims.png" alt="Agreement outcomes under sparse and dense contacts, exact filled-versus-wireframe control, and copying credit by seat"><figcaption>256 main blocks and 64 initiative-sensitivity blocks per scenario. Whiskers show 95% Wilson simulation-sampling intervals. The complete graph makes all seats structurally equivalent; small differences among those seats are sampling variation.</figcaption></figure>
<details><summary>Main topology SIMS results</summary>{table(0)}</details><details><summary>Initiative sensitivity: probability 0.02</summary>{table(.02)}</details>
<h3>Position and identity remain separate tests</h3><p>All 48 rotations/reflections of the finite Menger construction preserve its contact graph. They group the positions into eight equivalent corners with three contacts each, and twelve equivalent edge seats with two contacts each. A graph symmetry cannot exchange those two types because their degrees differ. On the complete graph every seat is structurally equivalent. Identity labels still have no behavioral effect under the specified copying rule.</p>
<h3>What the algebra checks establish</h3><p>Finite lifting succeeds after a four-vertex refinement in the selected example, while a compatible extra prescription can still block a lift. Simplicial faces delete vertices and degeneracies repeat them; barycentric checks make the gluing and collapse picture exact. The category-nerve example composes arrows by addition modulo 3 and inserts the identity arrow. Cube connections use max of neighboring coordinates, which matches the supplied relation involving insertion of zero.</p>
<p>The <a href="https://arxiv.org/html/1803.02516v3">Menger-prespace paper</a> concerns an infinite generic limit with stronger extension properties. Our finite graph tests check prerequisites and counterexamples; they do not certify that generic limit or its lifting theorem. Its graph-theoretic connectedness also differs from connectedness of the underlying zero-dimensional topological space. The simplicial background is in <a href="https://arxiv.org/abs/0809.4221v8">Friedman's illustrated introduction</a>.</p>
<p><a href="TOPOLOGY_TESTS.md">Test design and interpretation</a> · <a href="topology_results.json">All saved outcomes</a> · <code>python topology.py --check</code></p></section>'''


if __name__=='__main__':build_figures();print('Built two topology test figures.')
