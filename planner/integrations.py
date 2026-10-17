import os,json,urllib.request,urllib.parse
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
