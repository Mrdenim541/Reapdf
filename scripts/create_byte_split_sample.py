"""Synthetic native PDF with distinct incompressible images; isolated runtime safe."""
from pathlib import Path
import random
import pymupdf as f


def create():
    with f.open() as d:
        for i in range(3):
            p=d.new_page(width=250,height=350);p.insert_text((20,50),f'SIZEPAGE {i+1} UNCHANGED')
            pix=f.Pixmap(f.csRGB,128,128,random.Random(80+i).randbytes(128*128*3),False)
            p.insert_image(f.Rect(20,80,148,208),pixmap=pix);p.set_rotation(90 if i==1 else 0)
        return d.tobytes()


if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_bytes(create())
