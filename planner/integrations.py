import os,json,urllib.request,urllib.parse,hashlib,time
from datetime import timedelta
from django.utils import timezone
class IntegrationError(Exception): pass
def call(url,data=None,headers=None):
    try:
        req=urllib.request.Request(url,data=data,headers=headers or {})
        with urllib.request.urlopen(req,timeout=12) as response: return json.load(response)
    except Exception as exc: raise IntegrationError('The external service could not complete the request. Check configuration and try again.') from exc
def required(name):
    value=os.environ.get(name)
    if not value: raise IntegrationError(f'{name} is not configured.')
    return value
def weather(profile):
    query=urllib.parse.urlencode({'latitude':profile.latitude,'longitude':profile.longitude,'daily':'precipitation_probability_max,temperature_2m_max','forecast_days':2,'timezone':'auto'})
    return call('https://api.open-meteo.com/v1/forecast?'+query)['daily']
def send_plan(email,body):
    if not email: raise IntegrationError('Add an email address to your account first.')
    return call('https://api.resend.com/emails',json.dumps({'from':required('RESEND_FROM'),'to':[email],'subject':'Your BeforeBed plan','text':body}).encode(),{'Authorization':'Bearer '+required('RESEND_API_KEY'),'Content-Type':'application/json'})
def upload_photo(file):
    cloud=required('CLOUDINARY_CLOUD_NAME'); key=required('CLOUDINARY_API_KEY'); secret=required('CLOUDINARY_API_SECRET')
    stamp=str(int(time.time())); signature=hashlib.sha1(('timestamp='+stamp+secret).encode()).hexdigest()
    boundary='BeforeBedUploadBoundary'
    body=b''
    for k,v in {'api_key':key,'timestamp':stamp,'signature':signature}.items():
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="photo"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+file.read()+f'\r\n--{boundary}--\r\n'.encode()
    return call(f'https://api.cloudinary.com/v1_1/{cloud}/image/upload',body,{'Content-Type':'multipart/form-data; boundary='+boundary})['secure_url']
def calendar_events(token):
    now=timezone.now(); query=urllib.parse.urlencode({'timeMin':now.isoformat(),'timeMax':(now+timedelta(days=2)).isoformat(),'singleEvents':'true','orderBy':'startTime','maxResults':15})
    return call('https://www.googleapis.com/calendar/v3/calendars/primary/events?'+query,headers={'Authorization':'Bearer '+token}).get('items',[])
