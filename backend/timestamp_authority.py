"""Explicit-trust RFC3161 requests over bounded, verified public HTTPS."""
import asyncio,hashlib,ipaddress,secrets,socket,threading
from datetime import datetime,timezone
from urllib.parse import urlsplit
import aiohttp
from asn1crypto import tsp
from cryptography import x509
from pyhanko.sign.timestamps import TimeStamper
from pyhanko.sign.validation import generic_cms
from pyhanko.sign.validation.status import TimestampSignatureStatus
from pyhanko_certvalidator import ValidationContext
from .engine import DocumentError
from .certificates import trust_certificates
from .timestamp_report import report

MAX_RESPONSE=512*1024
REQUEST_TIMEOUT=15


def settings(config,trust):
    if not isinstance(config,dict) or set(config)!={'url'} or not isinstance(config['url'],str):raise DocumentError('Configura la URL HTTPS de la autoridad de tiempo.')
    url=config['url']
    if not 1<=len(url)<=2048 or any(ord(c)<=32 or ord(c)>=127 for c in url) or '\\' in url:raise DocumentError('La URL TSA no es válida.')
    try:
        p=urlsplit(url);host=p.hostname;port=p.port or 443
        if p.scheme!='https' or not host or p.username is not None or p.password is not None or p.fragment or not 1<=port<=65535:raise ValueError()
        if host.endswith('.') or host.lower() in ['localhost'] or host.lower().endswith(('.localhost','.local','.internal')):raise ValueError()
        try:
            if not ipaddress.ip_address(host).is_global:raise ValueError()
        except ValueError:
            # DNS names are resolved immediately before a request. Reject IP
            # literals and numeric aliases that failed the public-IP test.
            if ':' in host or host.replace('.','').isdigit() or len(host)>253 or any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') or not all(c.isalnum() or c=='-' for c in label) for label in host.split('.')):raise ValueError()
    except ValueError:raise DocumentError('Usa una URL HTTPS pública, sin credenciales ni fragmentos; no se consultan redes locales.') from None
    roots=trust_certificates(trust)
    if not roots:raise DocumentError('Selecciona certificados públicos de confianza para la autoridad de tiempo.')
    return url,roots


async def _resolve(host,port,family=socket.AF_UNSPEC):
    # A cancelled getaddrinfo task in the default executor can keep
    # asyncio.run waiting for its worker during shutdown. Use a daemon resolver
    # and deliver results only while its event loop/future still exists.
    loop=asyncio.get_running_loop();future=loop.create_future()
    def complete(value,error):
        if not future.done():
            if error:future.set_exception(error)
            else:future.set_result(value)
    def run():
        try:value=socket.getaddrinfo(host,port,family=family,type=socket.SOCK_STREAM);error=None
        except Exception as exc:value=None;error=exc
        try:loop.call_soon_threadsafe(complete,value,error)
        except RuntimeError:pass
    threading.Thread(target=run,daemon=True).start()
    return await future


async def _check_public_host(host,port):
    try:addresses=await _resolve(host,port)
    except OSError:raise DocumentError('No se pudo resolver la autoridad de tiempo.') from None
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):raise DocumentError('La autoridad de tiempo no puede apuntar a una dirección local o reservada.')
    return addresses


class _Resolver(aiohttp.abc.AbstractResolver):
    def __init__(self,host,addresses):self.host=host;self.addresses=addresses
    async def resolve(self,host,port=0,family=socket.AF_INET):
        # Direct connections reuse the public addresses already checked. Proxy
        # hostnames still follow the configured environment, without a second
        # uncancellable system resolver or changing the request destination.
        rows=self.addresses if host==self.host else await _resolve(host,port,family)
        return [{'hostname':host,'host':r[4][0],'port':port,'family':r[0],'proto':r[2],'flags':socket.AI_NUMERICHOST} for r in rows]
    async def close(self):pass


async def exchange(url,request):
    p=urlsplit(url)
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            addresses=await _check_public_host(p.hostname,p.port or 443)
            connector={'connector':aiohttp.TCPConnector(resolver=_Resolver(p.hostname,addresses))} if addresses else {}
            async with aiohttp.ClientSession(trust_env=True,timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT,connect=5),auto_decompress=False,**connector) as session:
                async with session.post(url,data=request,headers={'Content-Type':'application/timestamp-query','Accept':'application/timestamp-reply','Accept-Encoding':'identity'},allow_redirects=False) as response:
                    if response.status!=200:raise DocumentError('La autoridad de tiempo no devolvió una respuesta válida; no se siguen redirecciones.')
                    if response.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/timestamp-reply' or response.headers.get('Content-Encoding','identity').lower() not in ['identity','']:raise DocumentError('La autoridad no devolvió un sello RFC3161 binario compatible.')
                    if response.content_length is not None and response.content_length>MAX_RESPONSE:raise DocumentError('La respuesta TSA supera 512 KB.')
                    chunks=[];total=0
                    async for chunk in response.content.iter_chunked(16384):
                        total+=len(chunk)
                        if total>MAX_RESPONSE:raise DocumentError('La respuesta TSA supera 512 KB.')
                        chunks.append(chunk)
                    return b''.join(chunks)
    except DocumentError:raise
    except (TimeoutError,aiohttp.ClientError,OSError,ValueError):raise DocumentError('No se pudo consultar la TSA por HTTPS verificado. Revisa conexión, URL y confianza TLS del equipo.') from None


class VerifiedTimeStamper(TimeStamper):
    def __init__(self,config,trust):
        super().__init__(include_nonce=True);self.url,self.roots=settings(config,trust);self.requests=0;self.last_report=None

    async def async_timestamp(self,message_digest,md_algorithm):
        if md_algorithm!='sha256' or not isinstance(message_digest,bytes) or len(message_digest)!=32:raise DocumentError('El sello solicitado necesita una huella SHA-256 válida.')
        self.requests+=1
        if self.requests>3:raise DocumentError('La operación superó el límite de solicitudes TSA.')
        nonce=secrets.randbits(128)|(1<<127)
        request=tsp.TimeStampReq({'version':1,'message_imprint':{'hash_algorithm':{'algorithm':'sha256'},'hashed_message':message_digest},'nonce':nonce,'cert_req':True})
        raw=await exchange(self.url,request.dump())
        try:
            if not isinstance(raw,bytes) or not raw or len(raw)>MAX_RESPONSE:raise ValueError()
            response=tsp.TimeStampResp.load(raw,strict=True)
            if response['status']['status'].native not in ['granted','granted_with_mods']:raise ValueError()
            token=response['time_stamp_token'];data=token['content'];info=data['encap_content_info']['content'].parsed
            if token['content_type'].native!='signed_data' or info['version'].native!='v1' or len(data['signer_infos'])!=1 or len(data['certificates'])>20:raise ValueError()
            if data['signer_infos'][0]['digest_algorithm']['algorithm'].native not in ['sha256','sha384','sha512'] or len(data['signer_infos'][0]['signature'].native)>8192:raise ValueError()
            # Bound public-key work before the cryptographic verifier runs,
            # rather than discovering an oversized RSA key after verification.
            for choice in data['certificates']:
                encoded=choice.chosen.dump()
                if choice.name!='certificate' or len(encoded)>65536:raise ValueError()
                public=x509.load_der_x509_certificate(encoded).public_key()
                if getattr(public,'key_size',0)>8192:raise ValueError()
            imprint=info['message_imprint']
            if info['nonce'].native!=nonce or imprint['hash_algorithm']['algorithm'].native!='sha256' or imprint['hashed_message'].native!=message_digest:raise ValueError()
            now=datetime.now(timezone.utc)
            if abs((info['gen_time'].native-now).total_seconds())>300:raise ValueError()
            context=ValidationContext(trust_roots=self.roots,allow_fetching=False,revocation_mode='soft-fail',moment=now)
            checked=await generic_cms.validate_tst_signed_data(data,context,lambda algorithm:message_digest if algorithm=='sha256' else b'')
            result=report(TimestampSignatureStatus(**checked),now,imprint_algorithm='sha256',token_info=info)
            if not result['time_accepted_offline']:raise ValueError()
            result.update(request_nonce_checked=True,response_imprint_checked=True,network_used=True,response_sha256=hashlib.sha256(raw).hexdigest())
            self.last_report=result
            return token
        except DocumentError:raise
        except Exception:raise DocumentError('La respuesta TSA no superó la comprobación de nonce, huella, fecha, firma o confianza. No se entrega una copia sellada.') from None
