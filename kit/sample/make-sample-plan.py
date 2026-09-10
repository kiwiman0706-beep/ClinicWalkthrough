#!/usr/bin/env python3
"""Draw the sample floor plans that ship with the kit.

A deliberately plain 1:50 plan of a fictional clinic, in the shape a real
architect's PDF comes in: hatched walls, door swing arcs, dimension strings and
room labels as vector text. It exists so the extraction workflow in GUIDE.md can
be rehearsed on something before the real drawing arrives.

    python3 kit/sample/make-sample-plan.py
"""
import math
import pathlib

import pymupdf

MM = 1 / 25.4 * 72 / 50           # 1 mm of building at 1:50, in PDF points
OX, OY = 150, 110                 # where the plan's 0,0 sits on the page
GREY = (0.1, 0.1, 0.1)


def P(x, z):
    """Building metres -> page points."""
    return pymupdf.Point(OX + x * 1000 * MM, OY + z * 1000 * MM)


class Sheet:
    def __init__(self, doc, title):
        self.page = doc.new_page(width=842, height=1191)   # A3 portrait
        self.shape = self.page.new_shape()
        self.title = title

    def wall(self, x0, z0, x1, z1):
        """A wall as the drawings show them: outline plus 45 degree hatching."""
        r = pymupdf.Rect(P(x0, z0), P(x1, z1))
        self.shape.draw_rect(r)
        self.shape.finish(color=GREY, width=1.1, fill=(1, 1, 1))
        step = 3.0
        start = r.x0 - r.height
        while start < r.x1:
            a = pymupdf.Point(max(start, r.x0), r.y0 + max(0, r.x0 - start))
            b = pymupdf.Point(min(start + r.height, r.x1), r.y0 + min(r.height, r.x1 - start))
            if b.x > a.x:
                self.shape.draw_line(a, b)
            start += step
        self.shape.finish(color=GREY, width=0.3)

    def door(self, hinge, radius, a0, a1, leaf):
        """Swing arc plus the closed leaf: the pair that pins a hinged door."""
        c = P(*hinge)
        pts = []
        for i in range(25):
            t = math.radians(a0 + (a1 - a0) * i / 24)
            pts.append(pymupdf.Point(c.x + radius * 1000 * MM * math.cos(t),
                                     c.y + radius * 1000 * MM * math.sin(t)))
        for i in range(len(pts) - 1):
            self.shape.draw_line(pts[i], pts[i + 1])
        self.shape.finish(color=GREY, width=0.4)
        self.shape.draw_rect(pymupdf.Rect(P(*leaf[0]), P(*leaf[1])))
        self.shape.finish(color=GREY, width=0.8, fill=(1, 1, 1))

    def slider(self, x0, z0, x1, z1):
        self.shape.draw_rect(pymupdf.Rect(P(x0, z0), P(x1, z1)))
        self.shape.finish(color=GREY, width=0.8, fill=(1, 1, 1))

    def label(self, x, z, text, size=8):
        self.shape.insert_text(P(x, z), text, fontname='japan', fontsize=size, color=GREY)

    def dim(self, x0, z0, x1, z1, text):
        self.shape.draw_line(P(x0, z0), P(x1, z1))
        self.shape.finish(color=GREY, width=0.3)
        for p in ((x0, z0), (x1, z1)):
            self.shape.draw_circle(P(*p), 1.2)
            self.shape.finish(color=GREY, fill=GREY)
        self.shape.insert_text(P((x0 + x1) / 2 - .35, (z0 + z1) / 2 - .08), text,
                               fontname='japan', fontsize=7, color=GREY)

    def close(self):
        self.shape.insert_text(pymupdf.Point(OX, 830), self.title,
                               fontname='japan', fontsize=13, color=GREY)
        self.shape.insert_text(pymupdf.Point(OX, 848),
                               'みどり内科クリニック（架空）　S=1:50　サンプル図面',
                               fontname='japan', fontsize=8, color=GREY)
        self.shape.commit()


T = 0.10          # internal partition thickness
OUTER = 0.10      # external wall thickness


def ground(doc):
    s = Sheet(doc, '1階平面図')
    # outer shell, left open where the shopfront glazing goes
    s.wall(0, 0, 9.0, OUTER)
    s.wall(0, 0, OUTER, 10.9)
    s.wall(8.9, 0, 9.0, 10.9)
    s.wall(0, 10.9, 2.2, 11.0)
    s.wall(6.4, 10.9, 9.0, 11.0)
    for x, z in ((0.10, 0.10), (8.55, 0.10), (0.10, 4.10), (8.55, 4.10), (0.10, 8.55), (8.55, 8.55)):
        s.wall(x, z, x + .35, z + .35)
    # corridor wall with three consulting-room doors
    for a, b in ((0.10, 0.60), (1.45, 3.55), (4.40, 6.55), (7.40, 8.90)):
        s.wall(a, 3.6, b, 3.6 + T)
    for hinge, leaf in ((0.60, (0.60, 1.45)), (3.55, (3.55, 4.40)), (6.55, (6.55, 7.40))):
        s.door((hinge, 3.6), 0.85, 270, 360, ((hinge, 2.75), (hinge + .045, 3.6)))
        s.slider(leaf[0], 3.6, leaf[1], 3.6 + T)
    s.wall(3.0, 0.20, 3.0 + T, 3.6)
    s.wall(6.0, 0.20, 6.0 + T, 3.6)
    # reception / waiting
    s.wall(0.10, 4.6, 5.2, 4.6 + T)
    s.wall(5.3, 4.6, 7.0, 4.6 + T)
    s.slider(7.0, 4.6, 7.9, 4.6 + T)
    s.wall(7.9, 4.6, 8.9, 4.6 + T)
    s.wall(5.2, 4.6, 5.2 + T, 7.1)
    s.wall(5.2, 7.9, 5.2 + T, 8.8)
    s.wall(5.2, 9.4, 5.2 + T, 9.5)
    s.door((5.2, 7.1), 0.80, 0, 90, ((5.2, 7.1), (5.2 + .045, 7.9)))
    s.slider(5.2, 8.8, 5.2 + T, 9.4)
    s.wall(5.3, 7.0, 7.0, 7.0 + T)
    s.wall(7.9, 7.0, 8.9, 7.0 + T)
    s.door((7.0, 7.0), 0.90, 0, 90, ((7.0, 7.0), (7.0 + .045, 7.9)))
    s.wall(6.6, 7.1, 6.6 + T, 10.9)
    s.wall(6.7, 7.1, 6.7 + T, 10.9)
    s.wall(5.3, 8.6, 6.6, 8.6 + T)
    s.wall(0.10, 9.5, 3.2, 9.5 + T)
    s.wall(3.2, 9.6, 3.2 + T, 10.9)
    s.wall(5.2, 9.6, 5.2 + T, 10.9)
    s.slider(3.6, 9.55, 4.6, 9.55 + 0.05)
    s.slider(3.2, 10.86, 4.2, 10.90)
    s.slider(4.2, 10.86, 5.2, 10.90)
    # stair going up, nine treads
    for i in range(9):
        s.shape.draw_line(P(6.90, 7.30 + i * .25), P(8.80, 7.30 + i * .25))
    s.shape.finish(color=GREY, width=0.4)
    s.label(7.5, 9.9, 'UP', 7)
    for x, z, t in ((1.1, 1.9, '診察室1'), (4.1, 1.9, '診察室2'), (7.1, 1.9, '処置室'),
                    (2.2, 7.0, '待合室'), (6.6, 5.8, '受付'), (5.5, 7.9, 'WC'),
                    (5.5, 9.9, '倉庫'), (7.3, 8.9, '階段室'), (3.7, 10.4, '風除室')):
        s.label(x, z, t)
    s.dim(0.05, -0.55, 8.95, -0.55, '9,000')
    s.dim(-0.55, 0.05, -0.55, 10.95, '11,000')
    s.dim(0.10, 3.35, 3.00, 3.35, '2,900')
    s.dim(5.30, 4.35, 8.90, 4.35, '3,600')
    s.close()


def upper(doc):
    s = Sheet(doc, '2階平面図')
    s.wall(0, 0, 9.0, OUTER)
    s.wall(0, 0, OUTER, 10.9)
    s.wall(8.9, 0, 9.0, 10.9)
    s.wall(0, 10.9, 9.0, 11.0)
    for x, z in ((0.10, 0.10), (8.55, 0.10), (0.10, 4.10), (8.55, 4.10), (0.10, 8.55), (8.55, 8.55)):
        s.wall(x, z, x + .35, z + .35)
    s.wall(4.4, 0.20, 4.4 + T, 4.5)
    for a, b in ((0.10, 1.60), (2.45, 6.10), (6.95, 8.90)):
        s.wall(a, 4.5, b, 4.5 + T)
    for hinge in (1.60, 6.10):
        s.door((hinge, 4.5 + T), 0.85, 0, 90, ((hinge, 4.6), (hinge + .045, 5.45)))
        s.slider(hinge, 4.5, hinge + .85, 4.5 + T)
    for a, b in ((0.10, 1.20), (2.05, 3.90), (4.70, 5.55), (6.30, 7.20), (8.05, 8.90)):
        s.wall(a, 5.6, b, 5.6 + T)
    for hinge, w in ((1.20, .85), (3.90, .80), (5.55, .75)):
        s.door((hinge, 5.6), w, 270, 360, ((hinge, 5.6 - w), (hinge + .045, 5.6)))
        s.slider(hinge, 5.6, hinge + w, 5.6 + T)
    s.slider(7.20, 5.6, 8.05, 5.6 + T)
    s.wall(3.4, 5.7, 3.4 + T, 10.9)
    s.wall(5.2, 5.7, 5.2 + T, 10.9)
    s.wall(3.5, 8.0, 3.9, 8.0 + T)
    s.slider(3.9, 8.0, 4.7, 8.0 + T)
    s.wall(4.7, 8.0, 5.2, 8.0 + T)
    s.wall(6.6, 5.7, 6.6 + T, 7.0)
    s.wall(5.3, 7.0, 6.6, 7.0 + T)
    s.wall(6.7, 7.0, 8.9, 7.0 + T)
    s.wall(6.6, 7.1, 6.7, 10.9)
    for i in range(9):
        s.shape.draw_line(P(6.90, 10.65 - i * .25), P(8.80, 10.65 - i * .25))
    s.shape.finish(color=GREY, width=0.4)
    s.label(7.5, 7.6, 'DN', 7)
    for x, z, t in ((1.8, 2.3, '事務室'), (6.2, 2.3, '会議室'), (4.0, 5.2, '廊下'),
                    (1.3, 8.3, '休憩室'), (3.9, 6.8, '更衣室'), (3.9, 9.5, '倉庫'),
                    (5.5, 6.5, 'WC'), (7.3, 6.5, '給湯室'), (7.3, 9.0, '階段室')):
        s.label(x, z, t)
    s.dim(0.05, -0.55, 8.95, -0.55, '9,000')
    s.dim(-0.55, 0.05, -0.55, 10.95, '11,000')
    s.close()


def main():
    here = pathlib.Path(__file__).resolve().parent
    doc = pymupdf.open()
    ground(doc)
    doc.save(here / 'sample-plan-1F.pdf')
    doc.close()
    doc = pymupdf.open()
    upper(doc)
    doc.save(here / 'sample-plan-2F.pdf')
    doc.close()
    print('wrote sample-plan-1F.pdf / sample-plan-2F.pdf')


if __name__ == '__main__':
    main()
