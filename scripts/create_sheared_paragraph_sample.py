"""Generic mixed-shear paragraph; no external assets or personal document data."""
import pymupdf as f


def create():
    d=f.open();p=d.new_page(width=650,height=800);p.insert_font(fontname='hebo');p.insert_font(fontname='heit');p.insert_text((30,740),'NEIGHBOR UNCHANGED')
    advance=f.Font('hebo').text_length('HELLO ',fontsize=18)
    data=f'q BT /hebo 18 Tf .8 0 0 rg 1 0 0 1 200 400 Tm (HELLO ) Tj /heit 14 Tf 0 0 .8 rg 1 0 .35 1 {200+advance} 400 Tm (TEXT) Tj ET Q'.encode()
    x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,data);d.xref_set_key(p.xref,'Contents','['+' '.join(f'{r} 0 R' for r in p.get_contents()+[x])+']')
    d.new_page(width=650,height=800).insert_text((30,40),'OTHER PAGE UNCHANGED');d.new_page(width=650,height=800)
    result=d.tobytes();d.close();return result


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();Path(args.output).write_bytes(create())
