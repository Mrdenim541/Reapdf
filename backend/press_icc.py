"""Bounded local output-profile validation; never choose a press profile implicitly."""
from io import BytesIO
import hashlib,struct
from PIL import ImageCms
from .engine import DocumentError
MAX_ICC=2*1024*1024


def inspect(data,output=True):
    if not isinstance(data,bytes) or not 132<=len(data)<=MAX_ICC:raise DocumentError('El perfil ICC debe medir entre 132 bytes y 2 MiB.')
    size=struct.unpack_from('>I',data)[0];count=struct.unpack_from('>I',data,128)[0]
    if size!=len(data) or data[36:40]!=b'acsp' or data[8] not in [2,4] or not 1<=count<=512 or 132+count*12>len(data):raise DocumentError('La cabecera o tabla del perfil ICC no es válida.')
    seen=set()
    for i in range(count):
        name,offset,length=struct.unpack_from('>4sII',data,132+12*i)
        if name in seen or offset%4 or offset<132+12*count or length<8 or offset+length>len(data):raise DocumentError('El perfil ICC tiene etiquetas duplicadas o fuera de límites.')
        seen.add(name)
    try:
        profile=ImageCms.ImageCmsProfile(BytesIO(data));space=profile.profile.xcolor_space.strip();kind=profile.profile.device_class.strip();pcs=profile.profile.connection_space.strip()
        if space not in ['RGB','CMYK','GRAY'] or pcs not in ['XYZ','Lab'] or output and kind!='prtr':raise ValueError('Se necesita un perfil de salida de impresora RGB, CMYK o gris.')
        if output:ImageCms.buildTransformFromOpenProfiles(ImageCms.createProfile('sRGB'),profile,'RGB',{'RGB':'RGB','CMYK':'CMYK','GRAY':'L'}[space])
        description=ImageCms.getProfileDescription(profile).strip()[:200]
    except Exception as exc:raise DocumentError('El perfil no puede usarse como condición de salida: '+str(exc)[:180]) from exc
    return {'space':space,'channels':{'RGB':3,'CMYK':4,'GRAY':1}[space],'class':kind,'major_version':data[8],'description':description,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'scope':'Estructura y transformación ICC comprobadas con LittleCMS; no valida el comportamiento físico de la imprenta.'}
