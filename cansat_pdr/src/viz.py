"""Render 3D fuera de pantalla de las piezas CAD (PyVista)."""
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True


def mesh_of(shape, tol=0.08, ang=0.25):
    verts, tris = shape.tessellate(tol, ang)
    pts = np.array([[v.x, v.y, v.z] for v in verts], float)
    faces = np.hstack([np.full((len(tris), 1), 3), np.array(tris, int)]).ravel()
    return pv.PolyData(pts, faces)


VIEWS = {
    # (direccion de la camara hacia el modelo, vector arriba)
    "iso": ((-1.0, -1.25, 0.75), (0, 0, 1)),
    "iso_cola": ((1.0, -1.2, 0.8), (0, 0, 1)),
    "iso_abajo": ((-1.0, -1.2, -0.7), (0, 0, 1)),
    "planta": ((0, 0, 1), (-1, 0, 0)),
    "lateral": ((0, -1, 0), (0, 0, 1)),
    "frente": ((-1, 0, 0), (0, 0, 1)),
    "vertical": ((-0.45, -1.3, 0.35), (1, 0, 0)),     # eje x hacia abajo: como cuelga del paracaidas
}


def render(parts, path, view="iso", size=(1600, 1200), zoom=1.25, opac=None, hide=(), edges=True,
           background="white", parallel=True, clip=None, marcas=None):
    """opac: dict nombre-parcial -> opacidad.  hide: nombres parciales a omitir.
    clip: (normal, origen) para cortar el modelo y ver el interior."""
    opac = opac or {}
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background(background)
    for p in parts:
        if any(h in p["nombre"] for h in hide) or any(h == p["grupo"] for h in hide):
            continue
        m = mesh_of(p["shape"])
        if clip is not None:
            m = m.clip(normal=clip[0], origin=clip[1])
            if m.n_points == 0:
                continue
        o = 1.0
        for k, v in opac.items():
            if k in p["nombre"] or k == p["grupo"]:
                o = v
        pl.add_mesh(m, color=p["color"], opacity=o, smooth_shading=True, split_sharp_edges=True,
                    specular=0.25, specular_power=20, ambient=0.25, diffuse=0.8)
        if edges and o > 0.6:
            fe = m.extract_feature_edges(feature_angle=35, boundary_edges=True, manifold_edges=False)
            if fe.n_points:
                pl.add_mesh(fe, color=(0.05, 0.05, 0.05), line_width=1.2)
    d, up = VIEWS[view] if isinstance(view, str) else view
    pl.view_vector([-d[0], -d[1], -d[2]] if False else d, viewup=up)
    if parallel:
        pl.enable_parallel_projection()
    pl.camera.zoom(zoom)
    pl.enable_anti_aliasing("ssaa")
    pl.screenshot(path)
    out = {}
    if marcas:
        ren = pl.renderer
        for k, p in marcas.items():
            ren.SetWorldPoint(p[0], p[1], p[2], 1.0)
            ren.WorldToView()
            v = ren.GetViewPoint()
            out[k] = (0.5 * (v[0] + 1), 1 - 0.5 * (v[1] + 1))       # fraccion del ancho / alto, origen arriba-izquierda
    pl.close()
    return out
