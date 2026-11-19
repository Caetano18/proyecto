"""Version en ingles de las figuras (para las laminas del PDR en la plantilla de la competencia).

Con FIG_LANG=en, cada figura de matplotlib se guarda ademas traducida, con el sufijo _en en el nombre
(la version en castellano del informe no cambia).  Los textos se traducen con traduccion_en.json
(texto exacto -> traduccion); los que no estan se anotan en faltan_en.txt para completarlos.
Las comas decimales pasan a punto.
"""
import os
import re
import json
import matplotlib
from matplotlib.figure import Figure

_DIR = os.path.dirname(os.path.abspath(__file__))
_DIC = os.path.join(_DIR, "traduccion_en.json")
_FALTAN = os.path.join(_DIR, "faltan_en.txt")
_orig_savefig = Figure.savefig
_LETRAS = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{2,}")


def _dic():
    try:
        return json.load(open(_DIC, encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _decimal(s):
    return re.sub(r"(?<=\d),(?=\d)", ".", s)


def traducir(s, dic):
    if s in dic:
        return dic[s], True
    for k, v in dic.items():                 # reglas con expresion regular (rotulos con valores calculados)
        if k.startswith("re:"):
            m = re.fullmatch(k[3:], s, flags=re.S)
            if m:
                return _decimal(m.expand(v)), True
    if not _LETRAS.search(s):
        return _decimal(s), True
    # traduccion por lineas (rotulos de varias lineas)
    if "\n" in s:
        partes = [traducir(x, dic) for x in s.split("\n")]
        if all(ok for _, ok in partes):
            return "\n".join(t for t, _ in partes), True
    return _decimal(s), False


def _savefig(self, fname, *args, **kwargs):
    if os.environ.get("FIG_LANG") == "en":
        # primero la version original (castellano)
        _orig_savefig(self, fname, *args, **kwargs)
        dic = _dic()
        faltan = []
        guardados = []
        for t in self.findobj(matplotlib.text.Text):
            s = t.get_text()
            if not s:
                continue
            n, ok = traducir(s, dic)
            if not ok:
                faltan.append(s)
            guardados.append((t, s))
            t.set_text(n)
        if faltan:
            with open(_FALTAN, "a", encoding="utf-8") as f:
                for s in faltan:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
        base, ext = os.path.splitext(str(fname))
        r = _orig_savefig(self, base + "_en" + ext, *args, **kwargs)
        for t, s in guardados:            # deja la figura como estaba
            t.set_text(s)
        return r
    return _orig_savefig(self, fname, *args, **kwargs)


Figure.savefig = _savefig
