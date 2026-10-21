import os,json,urllib.request,urllib.parse,urllib.error
from datetime import timedelta
from django.utils import timezone
class IntegrationError(Exception): pass
def call(url,data=None,headers=None,method=None):
    try:
        request_headers={'User-Agent':'BeforeBed/1.0 (Django student project)','Accept':'application/json'}
        request_headers.update(headers or {})
        req=urllib.request.Request(url,data=data,headers=request_headers,method=method)
        with urllib.request.urlopen(req,timeout=12) as response: return json.load(response)
    except urllib.error.HTTPError as exc:
        raw=exc.read().decode('utf-8','replace')
        try:
            detail=json.loads(raw).get('message') or json.loads(raw).get('error')
        except (json.JSONDecodeError,AttributeError):
            detail=raw.strip()
        message=f'The external service rejected the request ({exc.code}).'
        if detail and len(str(detail))<=240:
            message+=f' {detail}'
        raise IntegrationError(message) from exc
    except Exception as exc: raise IntegrationError('The external service could not complete the request. Check your connection and try again.') from exc
def required(name):
    value=os.environ.get(name)
    if not value: raise IntegrationError(f'{name} is not configured.')
    return value
def weather(profile):
    query=urllib.parse.urlencode({'latitude':profile.latitude,'longitude':profile.longitude,'daily':'precipitation_probability_max,temperature_2m_max','forecast_days':2,'timezone':'auto'})
    return call('https://api.open-meteo.com/v1/forecast?'+query)['daily']
def geocode_city(name):
    name=name.strip()
    if len(name)<2:
        raise IntegrationError('Enter at least two characters for the city name.')
    query=urllib.parse.urlencode({'name':name,'count':1,'language':'en','format':'json'})
    results=call('https://geocoding-api.open-meteo.com/v1/search?'+query).get('results',[])
    if not results:
        raise IntegrationError('No matching city was found. Try adding the country name.')
    place=results[0]
    if 'latitude' not in place or 'longitude' not in place:
        raise IntegrationError('The location service returned an incomplete result.')
    return place
def calendar_events(token):
    now=timezone.now(); query=urllib.parse.urlencode({'timeMin':now.isoformat(),'timeMax':(now+timedelta(days=2)).isoformat(),'singleEvents':'true','orderBy':'startTime','maxResults':15})
    return call('https://www.googleapis.com/calendar/v3/calendars/primary/events?'+query,headers={'Authorization':'Bearer '+token}).get('items',[])

def sync_calendar_event(token,task,start,end):
    payload=json.dumps({
        'summary':task.title,
        'description':f'Planned by BeforeBed. Task deadline: {task.deadline.isoformat()}',
        'start':{'dateTime':start.isoformat()},
        'end':{'dateTime':end.isoformat()},
    }).encode('utf-8')
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
    base='https://www.googleapis.com/calendar/v3/calendars/primary/events'
    if task.google_event_id:
        event_id=urllib.parse.quote(task.google_event_id,safe='')
        return call(f'{base}/{event_id}',payload,headers,method='PATCH')
    return call(base,payload,headers,method='POST')

def public_holidays(country_code,year):
    code=(country_code or '').strip().upper()
    if len(code)!=2 or not code.isalpha():
        raise IntegrationError('Enter a valid two-letter country code, such as SG or PH.')
    return call(f'https://date.nager.at/api/v3/PublicHolidays/{int(year)}/{code}')

def send_email(recipient,subject,body):
    api_key=required('RESEND_API_KEY')
    sender=os.environ.get('RESEND_FROM','BeforeBed <onboarding@resend.dev>')
    payload=json.dumps({'from':sender,'to':[recipient],'subject':subject,'text':body}).encode('utf-8')
    return call('https://api.resend.com/emails',payload,{
        'Authorization':f'Bearer {api_key}',
        'Content-Type':'application/json',
    })
