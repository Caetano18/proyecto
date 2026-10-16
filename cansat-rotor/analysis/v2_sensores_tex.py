#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera los fragmentos LaTeX (tablas de decisión) del capítulo de sensores a partir de sensores_decision.json.
Uso: python3 analysis/v2_sensores_tex.py"""
import os, json
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(R, 'analysis', 'data', 'sensores_decision.json')))
SLUG = ['pres', 'temp', 'imu', 'mag', 'ina', 'gps', 'radio', 'cam', 'mcu', 'act', 'hall', 'sep', 'mem', 'bat']
claves = list(d)
assert len(claves) == len(SLUG), (len(claves), len(SLUG))
def cm(x, fmt='%.2f'):
    return (fmt % x).replace('.', '{,}')
def esc(t):
    return t.replace('%', r'\%').replace('&', r'\&').replace('_', r'\_')
filas_prob = []
for k, slug in zip(claves, SLUG):
    v = d[k]; n = len(v['criterios']); excl = v.get('excluidas', {})
    best = max(range(len(v['candidatos'])), key=lambda i: v['prob_ganador'][i])
    L = [r'{\setlength{\tabcolsep}{4pt}', r'\begin{tabular}{@{}p{5.2cm}' + 'c' * n + r'|rrrr@{}}', r'\toprule',
         r'\textbf{Opción} & ' + ' & '.join('C%d' % (j + 1) for j in range(n)) + r' & \textbf{Suma} & \textbf{TOPSIS} & \textbf{$P_{\text{gana}}$} & \textbf{$P^{\pm1}$}\\', r'\midrule']
    L.append(r'\textit{peso} & ' + ' & '.join('%d' % round(100 * w) for w in v['pesos']) + r' & & & &\\\midrule')
    for i, c in enumerate(v['candidatos']):
        nom = esc(c)
        if c in excl:
            fila = r'%s${}^{\ast}$ & ' % nom + ' & '.join('%d' % x for x in v['puntajes'][i]) + r' & %s & %s & \textit{excl.} & \textit{excl.}\\' % (cm(v['suma'][i]), cm(v['topsis'][i]))
        else:
            pg = cm(v['prob_ganador'][i])
            pp = cm(v['prob_ganador_pun'][i])
            if i == best: pg = r'\textbf{%s}' % pg; nom = r'\textbf{%s}' % nom; pp = r'\textbf{%s}' % pp
            fila = r'%s & ' % nom + ' & '.join('%d' % x for x in v['puntajes'][i]) + r' & %s & %s & %s & %s\\' % (cm(v['suma'][i]), cm(v['topsis'][i]), pg, pp)
        L.append(fila)
    L += [r'\bottomrule', r'\end{tabular}}']
    leyenda = '; '.join('C%d %s' % (j + 1, esc(c)) for j, c in enumerate(v['criterios']))
    L.append(r'\par\smallskip\begin{minipage}{0.96\linewidth}\footnotesize\raggedright \textbf{Criterios} (peso en \%): ' + leyenda + '.')
    for c, motivo in excl.items():
        L.append(r' ${}^{\ast}$ Excluida por un requisito: %s.' % esc(motivo))
    L.append(r'\end{minipage}')
    open(os.path.join(R, 'figuras', 'sens_%s.tex' % slug), 'w').write('\n'.join(L) + '\n')
    # componente del equipo = el que lleva "(equipo" o "equipo" en el nombre; si no hay, la primera opción no aplica
    eq = [i for i, c in enumerate(v['candidatos']) if 'equipo' in c]
    filas_prob.append((slug, k, v['prob_ganador'][eq[0]] if eq else None, max(v['prob_ganador']), v['candidatos'][best]))
with open(os.path.join(R, 'analysis', 'data', 'sensores_prob.dat'), 'w') as f:
    f.write('slug p_equipo p_mejor\n')
    for slug, k, pe, pm, g in filas_prob:
        f.write('%s %s %.3f\n' % (slug, ('%.3f' % pe) if pe is not None else '0.000', pm))
for r in filas_prob: print(r)
