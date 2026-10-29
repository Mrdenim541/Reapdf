"""Generate a per-user Open With registration for review; never applies it."""
from pathlib import PureWindowsPath


def registration(executable):
    path=PureWindowsPath(executable)
    if not path.is_absolute() or path.name.lower()!='reapdf.exe' or any(c in str(path) for c in ['"','\n','\r','\0','%']):raise ValueError('Indica una ruta absoluta de Windows a Reapdf.exe.')
    def quoted(value):return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'
    command=quoted('"'+str(path)+'" "%1"')
    return '\r\n'.join(['Windows Registry Editor Version 5.00','',
        '[HKEY_CURRENT_USER\\Software\\Classes\\Reapdf.PDF]','@="Documento PDF (Reapdf)"',
        '[HKEY_CURRENT_USER\\Software\\Classes\\Reapdf.PDF\\shell\\open\\command]','@='+command,
        '[HKEY_CURRENT_USER\\Software\\Classes\\Applications\\Reapdf.exe]','"FriendlyAppName"="Reapdf"',
        '[HKEY_CURRENT_USER\\Software\\Classes\\Applications\\Reapdf.exe\\SupportedTypes]','".pdf"=""',
        '[HKEY_CURRENT_USER\\Software\\Classes\\Applications\\Reapdf.exe\\shell\\open\\command]','@='+command,
        '[HKEY_CURRENT_USER\\Software\\Classes\\.pdf\\OpenWithProgids]','"Reapdf.PDF"=""',''])


def removal():
    return '\r\n'.join(['Windows Registry Editor Version 5.00','',
        '[-HKEY_CURRENT_USER\\Software\\Classes\\Reapdf.PDF]',
        '[-HKEY_CURRENT_USER\\Software\\Classes\\Applications\\Reapdf.exe]',
        '[HKEY_CURRENT_USER\\Software\\Classes\\.pdf\\OpenWithProgids]','"Reapdf.PDF"=-',''])


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description='Preparar una asociación Abrir con, sin aplicarla.')
    parser.add_argument('--executable');parser.add_argument('--output',required=True);parser.add_argument('--remove',action='store_true')
    args=parser.parse_args()
    text=removal() if args.remove else registration(args.executable or '')
    Path(args.output).write_text(text,encoding='utf-16',newline='')
