"""Excerpt (not standalone): from a product photo to a catalogue photo, on the shop PC.

The AI (a local U2-Net model) only answers one question: which pixels are
the product? Everything around it is plain, tested code: a quality gate,
straightening and the final composition. Names are kept as in the project.

This is not a runnable module: helpers such as _puntos, limpiar_mascara, enderezar,
mejorar and componer live in the full, private module and are not included here.
"""

import numpy as np
from PIL import Image

LADO_LIMPIEZA = 200   # a small copy is enough to measure the mask (fast)
GIRO_MAXIMO = 25      # more tilted than this may be intentional (lying down)
GIRO_MINIMO = 1.0     # under one degree: leave it alone (rotating blurs a bit)


class FondoNoLimpio(ValueError):
    """The product could not be separated cleanly: the photo is not used."""


def comprobar(mascara: Image.Image) -> None:
    """Quality gate. Raises FondoNoLimpio if the cut-out is not reliable."""
    m = np.asarray(mascara.resize((LADO_LIMPIEZA, LADO_LIMPIEZA), Image.BILINEAR)).astype(np.float32) / 255
    producto = (m > 0.5).mean()
    if producto < 0.02:
        raise FondoNoLimpio("The product cannot be seen in the photo")
    if producto > 0.97:
        raise FondoNoLimpio("The background cannot be seen: the product fills it")
    candidatos = m > 0.15
    dudosos = ((m > 0.15) & (m < 0.85)).sum() / max(candidatos.sum(), 1)
    if dudosos > 0.35:                      # the model is unsure where the product ends
        raise FondoNoLimpio("It is not clear where the product ends")


def angulo_inclinacion(mascara: Image.Image) -> float:
    """Degrees to rotate so the product stands straight.

    Finds the rotation that makes the box around the product as small as
    possible (the minimum rectangle): in that pose the sides of the box, the
    can or the bottle are upright. Coarse search first, then refine to 0.1."""
    puntos = _puntos(mascara)               # (x, y) of product pixels, small copy
    if len(puntos) < 50:
        return 0.0
    puntos -= puntos.mean(axis=0)

    def area(grados: float) -> float:
        r = np.radians(grados)
        x = puntos[:, 0] * np.cos(r) - puntos[:, 1] * np.sin(r)
        y = puntos[:, 0] * np.sin(r) + puntos[:, 1] * np.cos(r)
        return float(np.ptp(x) * np.ptp(y))

    candidatos = np.arange(-GIRO_MAXIMO - 15, GIRO_MAXIMO + 15.01, 0.5)
    mejor = min(candidatos, key=area)
    finos = np.arange(mejor - 0.5, mejor + 0.51, 0.1)
    mejor = float(min(finos, key=area))
    if abs(mejor) > GIRO_MAXIMO or abs(mejor) < GIRO_MINIMO:
        return 0.0
    return round(mejor, 1)


def foto_profesional(imagen: Image.Image, segmentar) -> Image.Image:
    """Product photo -> catalogue photo: no background, straight, bright, sharp,
    on white. `segmentar(imagen) -> mask` is the AI."""
    mascara = limpiar_mascara(segmentar(imagen))    # drop stray blobs, soften edge
    comprobar(mascara)                              # no photo is better than a bad one
    imagen, mascara = enderezar(imagen, mascara)    # straighten up to 25 degrees
    return componer(mejorar(imagen, mascara), mascara)   # light/colour, then white card + soft shadow
