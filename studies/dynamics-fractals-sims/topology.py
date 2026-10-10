"""Finite graph and simplicial tests inspired by the supplied topology slides.

These computations do not construct the infinite generic Menger prespace.
Graph relations here are reflexive and symmetric; SIMS contacts omit self-loops.
"""
import argparse
from collections import Counter
from fractions import Fraction
from itertools import combinations, combinations_with_replacement, product, permutations
import json
import math
from pathlib import Path
import random
from models import menger_cells, menger_graph
from sims import run, seed_for, wilson


def graph(n, edges):
    if n < 1: raise ValueError('A graph needs vertices')
    rows=[{i} for i in range(n)]
    for a,b in edges:
        if not 0<=a<n or not 0<=b<n: raise ValueError('Invalid vertex')
        rows[a].add(b);rows[b].add(a)
    return tuple(tuple(sorted(row)) for row in rows)


def reflexive(adjacency):
    return graph(len(adjacency),((i,j) for i,row in enumerate(adjacency) for j in row))


def edges(G, loops=True):
    return {(i,j) for i,row in enumerate(G) for j in row if i<=j and (loops or i!=j)}


def connected(G, subset=None):
    nodes=set(range(len(G))) if subset is None else set(subset)
    if not nodes: return False
    visited={min(nodes)}; todo=list(visited)
    while todo:
        for j in set(G[todo.pop()]) & nodes - visited:
            visited.add(j);todo.append(j)
    return visited==nodes


def map_audit(source, target, mapping):
    valid=len(mapping)==len(source) and all(isinstance(j,int) and 0<=j<len(target) for j in mapping)
    if not valid: raise ValueError('Map must assign every source vertex to a target vertex')
    image_edges={tuple(sorted((mapping[i],mapping[j]))) for i,j in edges(source)}
    fibers=[tuple(i for i,v in enumerate(mapping) if v==j) for j in range(len(target))]
    report={'homomorphism':image_edges<=edges(target),
            'vertex_surjective':set(mapping)==set(range(len(target))),
            'edge_surjective':edges(target)<=image_edges,
            'connected_fibers':all(connected(source,fiber) for fiber in fibers),
            'source_connected':connected(source),'target_connected':connected(target),
            'fiber_sizes':[len(fiber) for fiber in fibers]}
    report['connected_epimorphism']=all(report[key] for key in (
        'homomorphism','vertex_surjective','edge_surjective','connected_fibers',
        'source_connected','target_connected'))
    return report


def compose(outer, inner):
    return tuple(outer[i] for i in inner)


def pullback(B,C,A,g,f):
    if not map_audit(B,A,g)['connected_epimorphism'] or not map_audit(C,A,f)['connected_epimorphism']:
        raise ValueError('Input maps must be connected epimorphisms')
    pairs=tuple((b,c) for b in range(len(B)) for c in range(len(C)) if g[b]==f[c])
    D=graph(len(pairs),((i,j) for i,(b,c) in enumerate(pairs) for j,(bb,cc) in enumerate(pairs)
                         if bb in B[b] and cc in C[c]))
    return D,tuple(b for b,c in pairs),tuple(c for b,c in pairs),pairs


def lifts(source,B,A,f,g,prescribed=None):
    """Exhaustively find connected-epimorphism lifts of a small finite problem."""
    prescribed={} if prescribed is None else dict(prescribed)
    if len(source)>8: raise ValueError('Exhaustive lifting is limited to eight source vertices')
    if len(f)!=len(source) or len(g)!=len(B): raise ValueError('Map size mismatch')
    if not map_audit(source,A,f)['connected_epimorphism'] or not map_audit(B,A,g)['connected_epimorphism']:
        raise ValueError('Base maps must be connected epimorphisms')
    if any(not 0<=i<len(source) or not 0<=j<len(B) for i,j in prescribed.items()):
        raise ValueError('Invalid prescribed vertex')
    choices=[tuple(j for j in range(len(B)) if g[j]==f[i] and (i not in prescribed or j==prescribed[i]))
             for i in range(len(source))]
    return [tuple(h) for h in product(*choices) if map_audit(source,B,h)['connected_epimorphism']]


def transitivity_witness(G):
    for x,row in enumerate(G):
        for y in row:
            for z in G[y]:
                if z not in row: return (x,y,z)
    return None


def transitive_closure(G):
    rows=[]
    for i in range(len(G)):
        seen={i};todo=[i]
        while todo:
            for j in set(G[todo.pop()])-seen:
                seen.add(j);todo.append(j)
        rows.append(tuple(sorted(seen)))
    return tuple(rows)


def reachable(G,start,end):
    seen={start};todo=[start]
    while todo:
        for j in set(G[todo.pop()])-seen:
            seen.add(j);todo.append(j)
    return end in seen


def menger_parent(level):
    if level<1: raise ValueError('Parent map starts at level >= 1')
    parent={p:i for i,p in enumerate(menger_cells(level-1))}
    return tuple(parent[tuple(c//3 for c in p)] for p in menger_cells(level))


def menger_symmetries():
    cells=menger_cells(1);index={p:i for i,p in enumerate(cells)}
    G=reflexive(menger_graph(1));maps=[]
    for order in permutations(range(3)):
        for flips in product((False,True),repeat=3):
            mapping=tuple(index[tuple(2-p[axis] if flip else p[axis] for axis,flip in zip(order,flips))]
                          for p in cells)
            if len(set(mapping))!=20 or {tuple(sorted((mapping[a],mapping[b]))) for a,b in edges(G)}!=edges(G):
                raise AssertionError('Cube symmetry does not preserve the graph')
            maps.append(mapping)
    orbits=sorted({tuple(sorted({m[i] for m in maps})) for i in range(20)})
    return {'verified_coordinate_symmetries':len(set(maps)),
            'orbits':[{'seats':orbit,'size':len(orbit),'contact_degree':len(G[orbit[0]])-1} for orbit in orbits]}


def face(simplex,i):
    if len(simplex)<2 or not 0<=i<len(simplex): raise ValueError('Invalid face index')
    return simplex[:i]+simplex[i+1:]


def degeneracy(simplex,i):
    if not simplex or not 0<=i<len(simplex): raise ValueError('Invalid degeneracy index')
    return simplex[:i]+(simplex[i],)+simplex[i:]


def standard_simplices(dimension, degree):
    if dimension<0 or degree<0: raise ValueError('Nonnegative dimensions required')
    return tuple(combinations_with_replacement(range(dimension+1),degree+1))


def nerve_face(chain,i,modulus=3):
    """Nerve of the one-object category with composition addition modulo 3."""
    if not chain or not 0<=i<=len(chain): raise ValueError('Invalid nerve face')
    if i==0: return chain[1:]
    if i==len(chain): return chain[:-1]
    return chain[:i-1]+((chain[i-1]+chain[i])%modulus,)+chain[i+1:]


def nerve_degeneracy(chain,i):
    if not 0<=i<=len(chain): raise ValueError('Invalid nerve degeneracy')
    return chain[:i]+(0,)+chain[i:]


def nerve_checks(max_degree=5):
    counts=Counter()
    for degree in range(max_degree+1):
        for chain in product(range(3),repeat=degree):
            if degree>=2:
                for i in range(degree+1):
                    for j in range(i+1,degree+1):
                        if nerve_face(nerve_face(chain,j),i)!=nerve_face(nerve_face(chain,i),j-1):
                            raise AssertionError('Nerve face composition')
                        counts['face_face']+=1
            for j in range(degree+1):
                for i in range(degree+2):
                    lhs=nerve_face(nerve_degeneracy(chain,j),i)
                    if i<j: rhs=nerve_degeneracy(nerve_face(chain,i),j-1)
                    elif i in (j,j+1): rhs=chain
                    else: rhs=nerve_degeneracy(nerve_face(chain,i-1),j)
                    if lhs!=rhs: raise AssertionError('Nerve identity insertion')
                    counts['face_degeneracy']+=1
                for i in range(j+1):
                    if nerve_degeneracy(nerve_degeneracy(chain,j),i)!=nerve_degeneracy(nerve_degeneracy(chain,i),j+1):
                        raise AssertionError('Nerve degeneracy composition')
                    counts['degeneracy_degeneracy']+=1
    return {'category':'One object; morphisms 0,1,2; composition addition mod 3; identity 0',
            'max_degree':max_degree,'by_family':dict(counts),'equalities_checked':sum(counts.values())}


def cube_face(point,i,value):
    if value not in (0,1) or not 0<=i<=len(point): raise ValueError('Invalid cube face')
    return point[:i]+(value,)+point[i:]


def cube_projection(point,i):
    if not 0<=i<len(point): raise ValueError('Invalid cube projection')
    return point[:i]+point[i+1:]


def cube_connection(point,i):
    if not 0<=i<len(point)-1: raise ValueError('Invalid cube connection')
    return point[:i]+(max(point[i],point[i+1]),)+point[i+2:]


def cubical_checks(max_dimension=4):
    counts=Counter()
    def check(name,left,right):
        if left!=right: raise AssertionError(name)
        counts[name]+=1
    for n in range(max_dimension+1):
        for p in product((Fraction(0),Fraction(1,3),Fraction(1)),repeat=n):
            for i in range(n+1):
                for a in (0,1):
                    check('projection_after_insert',cube_projection(cube_face(p,i,a),i),p)
                    for j in range(n):
                        left=cube_connection(cube_face(p,i,a),j)
                        if i<j: right=cube_face(cube_connection(p,j-1),i,a)
                        elif i in (j,j+1): right=p if a==0 else cube_face(cube_projection(p,j),j,a)
                        else: right=cube_face(cube_connection(p,j),i-1,a)
                        check('connection_face',left,right)
            for i in range(n-1):
                for j in range(n-1):
                    left=cube_projection(cube_connection(p,i),j)
                    if i<j: right=cube_connection(cube_projection(p,j+1),i)
                    elif i==j: right=cube_projection(cube_projection(p,i),i)
                    else: right=cube_connection(cube_projection(p,j),i-1)
                    check('projection_connection',left,right)
                    if i==j:
                        check('two_projection_forms',right,cube_projection(cube_projection(p,i+1),i))
            for i in range(n-2):
                check('max_associativity',cube_connection(cube_connection(p,i),i),
                      cube_connection(cube_connection(p,i+1),i))
                for j in range(i):
                    check('connection_connection',cube_connection(cube_connection(p,j),i),
                          cube_connection(cube_connection(p,i+1),j))
    return {'connection':'maximum of adjacent coordinates','coordinate_grid':['0','1/3','1'],
            'max_input_dimension':max_dimension,'by_family':dict(counts),
            'equalities_checked':sum(counts.values())}


def expected_block_change(G,state,mapping,refusal=Fraction(3,20)):
    """One uniformly chosen active seat copies a uniform neighbor, subject to refusal."""
    total=[Fraction(0) for _ in range(max(mapping)+1)]
    for i,row in enumerate(contacts(G)):
        if not row: raise ValueError('Copying requires a neighbor')
        drift=Fraction(sum(state[j] for j in row),len(row))-state[i]
        total[mapping[i]]+=(1-refusal)*drift/len(G)
    return tuple(total)


def aggregation_counterexample():
    G=graph(6,[(i,i+1) for i in range(5)]);target=graph(2,[(0,1)]);mapping=(0,0,0,1,1,1)
    states=[(0,0,1,0,0,1),(0,1,0,0,1,0)]
    counts=[[sum(s[i] for i in range(6) if mapping[i]==b) for b in (0,1)] for s in states]
    changes=[expected_block_change(G,s,mapping) for s in states]
    return {'source':'six-vertex path','projection':mapping,'map_audit':map_audit(G,target,mapping),
            'states':states,'ones_per_block':counts,'majority_colors':[[0,0],[0,0]],
            'microscopic_consensus':[False,False],
            'expected_change_in_block_ones':[[float(v) for v in c] for c in changes],
            'exact_expected_changes':[[str(v) for v in c] for c in changes],
            'interpretation':'Equal block counts have different next-step drift: counts alone do not close the copying dynamics.'}


def check_identities(max_degree=6):
    counts=Counter()
    for degree in range(max_degree+1):
        for s in standard_simplices(2,degree):
            if degree>=2:
                for i in range(degree+1):
                    for j in range(i+1,degree+1):
                        if face(face(s,j),i)!=face(face(s,i),j-1): raise AssertionError('face-face')
                        counts['face_face']+=1
            for j in range(degree+1):
                for i in range(degree+2):
                    lhs=face(degeneracy(s,j),i)
                    if i<j: rhs=degeneracy(face(s,i),j-1);name='face_degeneracy_left'
                    elif i in (j,j+1): rhs=s;name='face_degeneracy_identity'
                    else: rhs=degeneracy(face(s,i-1),j);name='face_degeneracy_right'
                    if lhs!=rhs: raise AssertionError(name)
                    counts[name]+=1
                for i in range(j+1):
                    if degeneracy(degeneracy(s,j),i)!=degeneracy(degeneracy(s,i),j+1):
                        raise AssertionError('degeneracy-degeneracy')
                    counts['degeneracy_degeneracy']+=1
    return dict(counts)


def insert_zero(weights,i):
    if not 0<=i<=len(weights): raise ValueError('Invalid face coordinate')
    return weights[:i]+(0,)+weights[i:]


def merge_weights(weights,i):
    if not 0<=i<len(weights)-1: raise ValueError('Invalid degeneracy coordinate')
    return weights[:i]+(weights[i]+weights[i+1],)+weights[i+2:]


def realize(simplex,weights,vertices):
    if len(simplex)!=len(weights) or any(w<0 for w in weights) or sum(weights)!=1:
        raise ValueError('One nonnegative barycentric weight per vertex, totaling exactly one')
    return tuple(sum(w*vertices[v][axis] for v,w in zip(simplex,weights))
                 for axis in range(len(vertices[0])))


def complex_from_facets(facets):
    return frozenset(tuple(c) for facet in facets for n in range(1,len(set(facet))+1)
                     for c in combinations(sorted(set(facet)),n))


def skeleton(complex_):
    vertices=sorted(s[0] for s in complex_ if len(s)==1)
    if vertices!=list(range(len(vertices))): raise ValueError('Use consecutive vertex labels')
    return graph(len(vertices),(s for s in complex_ if len(s)==2))


def boundary_columns(complex_,degree):
    if degree<1: return []
    lower=sorted(s for s in complex_ if len(s)==degree)
    index={s:i for i,s in enumerate(lower)}
    return [sum(1<<index[face(s,i)] for i in range(len(s)))
            for s in sorted(complex_) if len(s)==degree+1]


def gf2_rank(columns):
    pivots={}
    for column in columns:
        while column:
            pivot=column.bit_length()-1
            if pivot in pivots: column^=pivots[pivot]
            else: pivots[pivot]=column;break
    return len(pivots)


def homology(complex_):
    dimension=max(map(len,complex_))-1
    counts=[sum(len(s)==k+1 for s in complex_) for k in range(dimension+1)]
    ranks=[0]+[gf2_rank(boundary_columns(complex_,k)) for k in range(1,dimension+1)]+[0]
    betti=[counts[k]-ranks[k]-ranks[k+1] for k in range(dimension+1)]
    return {'simplex_counts':counts,'betti_Z2':betti,
            'euler_characteristic':sum((-1)**k*n for k,n in enumerate(counts))}


def triangle_chain(filled):
    triangles=[(0,1,2),(2,3,4),(4,5,6),(6,7,8)]
    facets=triangles if filled else [edge for t in triangles for edge in combinations(t,2)]
    return complex_from_facets(facets)


def mathematical_results():
    levels=[reflexive(menger_graph(i)) for i in range(3)]
    parents=[menger_parent(i) for i in (1,2)]
    projections=[]
    for i in (1,2):
        audit=map_audit(levels[i],levels[i-1],parents[i-1])
        if not audit['connected_epimorphism']: raise AssertionError('Menger projection')
        projections.append({'source_level':i,'target_level':i-1,**audit})
    paths=[(parents[0][parents[1][v]],parents[1][v],v) for v in range(400)]
    A=graph(2,[(0,1)]);B=graph(3,[(0,1),(1,2)]);C=B
    g=(0,0,1);f=(0,1,1)
    D,pB,pC,pairs=pullback(B,C,A,g,f)
    fD=compose(f,pC)
    successful=lifts(D,B,A,fD,g,{0:0,3:2})
    blocked=lifts(D,B,A,fD,g,{1:0})
    if compose(g,pB)!=fD or not successful or blocked: raise AssertionError('Finite lifting cases')
    vertices=((0,0),(1,0),(0,1));s=(0,1,2);p=(Fraction(2,5),Fraction(3,5))
    left=realize(face(s,0),p,vertices);right=realize(s,insert_zero(p,0),vertices)
    x=(0,1);q=(Fraction(1,5),Fraction(3,10),Fraction(1,2))
    collapsed_left=realize(degeneracy(x,1),q,vertices)
    collapsed_right=realize(x,merge_weights(q,1),vertices)
    if left!=right or collapsed_left!=collapsed_right: raise AssertionError('Gluing relation')
    examples={
        'triangle boundary':complex_from_facets([(0,1),(1,2),(0,2)]),
        'filled triangle':complex_from_facets([(0,1,2)]),
        'tetrahedron boundary':complex_from_facets(combinations(range(4),3)),
        'filled tetrahedron':complex_from_facets([tuple(range(4))]),
        'four triangle wireframe':triangle_chain(False),
        'four filled triangles':triangle_chain(True)}
    counts=check_identities()
    closure=transitive_closure(levels[1])
    return {'menger_projections':projections,'menger_finite_symmetries':menger_symmetries(),
            'compatible_prefixes':len(paths),'sample_prefixes':paths[:5],
            'finite_prefix_status':'A three-level truncation, not the infinite generic prespace.',
            'transitivity':{'level1_witness':transitivity_witness(levels[1]),
                            'original_edges_without_loops':len(edges(levels[1],False)),
                            'closure_edges_without_loops':len(edges(closure,False)),
                            'closure_equivalence_classes':1},
            'lifting':{'A_vertices':2,'B_vertices':3,'C_vertices':3,'D_vertices':len(D),
                       'g_B_to_A':g,'f_C_to_A':f,'D_pairs':pairs,'projection_to_B':pB,'projection_to_C':pC,
                       'projection_B_audit':map_audit(D,B,pB),'projection_C_audit':map_audit(D,C,pC),
                       'direct_lifts_from_C':len(lifts(C,B,A,f,g)),
                       'refined_lifts_with_endpoints_fixed':successful,
                       'compatible_but_blocked_prescription':{'source_vertex':1,'target_vertex':0,'lifts':len(blocked)}},
            'simplicial_identities':{'standard_simplex_dimension':2,'max_input_degree':6,
                                    'by_family':counts,'equalities_checked':sum(counts.values())},
            'category_nerve':nerve_checks(),'cubical_relations':cubical_checks(),
            'aggregation_counterexample':aggregation_counterexample(),
            'realization':{'face_gluing_equal':left==right,'face_common_point':[float(v) for v in left],
                           'degeneracy_collapse_equal':collapsed_left==collapsed_right,
                           'collapse_common_point':[float(v) for v in collapsed_left]},
            'homology':{name:homology(K) for name,K in examples.items()}}


def contacts(G):
    return tuple(tuple(j for j in row if j!=i) for i,row in enumerate(G))


def coordination_results(rounds=256,sensitivity_rounds=64,seed=20261010):
    M=reflexive(menger_graph(1));dense=transitive_closure(M)
    corner=max(range(20),key=lambda i:len(M[i]));edge=min(range(20),key=lambda i:len(M[i]))
    specs=[]
    for name,G in [('Menger contacts',M),('Transitive closure contacts',dense)]:
        for policy,seat,role in [('ordinary',corner,'baseline'),('oppose',corner,'corner'),('oppose',edge,'edge')]:
            specs.append((name,contacts(G),policy,seat,role))
    for filled in (False,True):
        specs.append(('Filled triangles' if filled else 'Triangle wireframe',contacts(skeleton(triangle_chain(filled))),
                      'ordinary',0,'baseline'))
    cases=[];pairs=[];exact_matches=0
    for initiative,count in [(0,rounds),(.02,sensitivity_rounds)]:
        runs=[[] for _ in specs]
        for block in range(count):
            order=list(range(len(specs)));random.Random(seed_for(seed,'order',initiative,block)).shuffle(order)
            for i in order:
                name,G,policy,seat,role=specs[i];n=len(G)
                rng=random.Random(seed_for(seed,'start',n,block));initial=[rng.randrange(2) for _ in range(n)]
                labels=list(range(n));random.Random(seed_for(seed,'identity',n,block)).shuffle(labels)
                row=run(G,initial,seed_for(seed,'dynamics',n,block),policy,seat,initiative,seat_to_id=labels)
                runs[i].append((block,row))
        runs=[sorted(x,key=lambda x:x[0]) for x in runs]
        for (block,left),(other,right) in zip(runs[6],runs[7]):
            if block!=other or left!=right: raise AssertionError('Same skeleton changed SIMS result')
            exact_matches+=1
        for i,(name,G,policy,seat,role) in enumerate(specs):
            rs=[r for _,r in runs[i]];success=sum(r['first_consensus'] is not None for r in rs)
            credits=[sum(r['credits_by_seat'][j] for r in rs) for j in range(len(G))]
            cases.append({'network':name,'sims':len(G),'policy':policy,'role':role,'focal_seat':seat,
                          'initiative':initiative,'rounds':count,'first_consensus_n':success,
                          'first_consensus_fraction':success/count,'wilson95':wilson(success,count),
                          'endpoint_fraction':sum(r['unanimous_at_end'] for r in rs)/count,
                          'mean_capped_seconds':sum(r['capped_time'] for r in rs)/count,
                          'mean_switches':sum(r['switches'] for r in rs)/count,
                          'mean_refusals':sum(r['refusals'] for r in rs)/count,
                          'mean_breaks':sum(r['breaks'] for r in rs)/count,
                          'copy_credit_by_seat':credits})
        for left,right in [(0,3),(1,4),(2,5),(6,7)]:
            for metric in ('first','endpoint','capped'):
                def value(row):
                    return int(row['first_consensus'] is not None) if metric=='first' else int(row['unanimous_at_end']) if metric=='endpoint' else row['capped_time']
                diffs=[value(b)-value(a) for (_,a),(_,b) in zip(runs[left],runs[right])]
                mean=sum(diffs)/count
                sem=math.sqrt(sum((d-mean)**2 for d in diffs)/(count-1)/count) if count>1 else 0
                pairs.append({'left':specs[left][0],'right':specs[right][0],'role':specs[left][4],
                              'initiative':initiative,'metric':metric,'right_minus_left':mean,
                              'paired_monte_carlo_normal95':[mean-1.96*sem,mean+1.96*sem]})
    return {'seed':seed,'data_kind':'SIMS simulation','new_rounds':8*(rounds+sensitivity_rounds),
            'horizon_seconds':120,'activation':.25,'refusal':.15,'cases':cases,'paired_comparisons':pairs,
            'exact_wireframe_filled_matched_pairs':exact_matches,
            'group_face_behavior':'Faces are not inputs to the existing pairwise copying rule.'}


def results():
    return {'mathematics':mathematical_results(),'sims':coordination_results()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();path=Path(__file__).with_name('topology_results.json');computed=results()
    if args.check:
        # JSON normalizes tuples to lists.
        if json.loads(json.dumps(computed))!=json.loads(path.read_text(encoding='utf-8')):
            raise SystemExit('FAIL: topology results differ.')
        print('PASS: finite topology checks and 2,560 SIMS runs reproduced.')
    else:
        path.write_text(json.dumps(computed,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('Saved finite topology checks and 2,560 SIMS runs.')
