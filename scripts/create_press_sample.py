"""Synthetic print document and explicitly synthetic RGB printer-declared ICC.

The fixture is for structural/round-trip tests, not a real press condition.
"""
import pymupdf as f
from PIL import ImageCms


def profile(cmyk=False):
    if cmyk:return cmyk_profile()
    data=bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes());data[12:16]=b'prtr';data[24:36]=__import__('struct').pack('>6H',2026,1,1,0,0,0);return bytes(data)


def create(embedded=False,cmyk=False):
    with f.open() as d:
        p=d.new_page(width=600,height=800)
        if embedded:p.insert_font(fontname='PressFont',fontbuffer=f.Font('helv').buffer)
        p.insert_text((45,70),'PRINT PREPARATION SAMPLE',fontname='PressFont' if embedded else 'helv');p.draw_rect(f.Rect(60,150,300,350),color=(0,1,1,0) if cmyk else (1,0,0),fill=(.4,.6,.8,0) if cmyk else (.4,.6,.8));q=d.new_page(width=600,height=800)
        if embedded:q.insert_font(fontname='PressFont',fontbuffer=f.Font('helv').buffer)
        q.insert_text((40,60),'OTHER PAGE UNCHANGED',fontname='PressFont' if embedded else 'helv');return d.tobytes()




def cmyk_profile():
    """Tiny synthetic ICC v2 LUT profile, not a real printing condition."""
    import struct,itertools
    def lut(inputs,outputs):
        header=b'mft1'+b'\0'*4+bytes([inputs,outputs,2,0])+struct.pack('>9i',65536,0,0,0,65536,0,0,0,65536)
        clut=bytes(int(round(v*255)) for cell in itertools.product([0,1],repeat=inputs) for v in (([(1-cell[0])*(1-cell[3]),(1-cell[1])*(1-cell[3]),(1-cell[2])*(1-cell[3])] if inputs==4 else [1-cell[0],1-cell[1],1-cell[2],0])))
        return header+bytes(range(256))*inputs+clut+bytes(range(256))*outputs
    text=b'SYNTHETIC CMYK TEST ONLY\0';desc=b'desc'+b'\0'*4+struct.pack('>I',len(text))+text+b'\0'*8+b'\0'*70
    tags=[(b'desc',desc),(b'cprt',b'text'+b'\0'*4+b'Synthetic software test\0'),(b'wtpt',b'XYZ '+b'\0'*4+struct.pack('>3i',63190,65536,54061)),(b'A2B0',lut(4,3)),(b'B2A0',lut(3,4))]
    header=bytearray(128);header[4:8]=b'lcms';header[8:12]=b'\x02\x10\0\0';header[12:24]=b'prtrCMYKXYZ ';header[24:36]=struct.pack('>6H',2026,1,1,0,0,0);header[36:40]=b'acsp';header[68:80]=struct.pack('>3i',63190,65536,54061);header[80:84]=b'TEST'
    offset=132+12*len(tags);table=[];parts=[]
    for key,data in tags:
        table.append(struct.pack('>4sII',key,offset,len(data)));padded=data+b'\0'*((-len(data))%4);parts.append(padded);offset+=len(padded)
    header[0:4]=struct.pack('>I',offset);return bytes(header)+struct.pack('>I',len(tags))+b''.join(table)+b''.join(parts)


if __name__=='__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(create(embedded=True));Path(sys.argv[1]+'.icc').write_bytes(profile())
