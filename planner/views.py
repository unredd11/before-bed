import os,secrets,urllib.parse,json
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from pathlib import Path
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import login,get_user_model
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Profile,Task,SleepEntry,ChecklistItem
from .forms import TaskForm,ProfileForm,SleepForm,ChecklistForm
from .planning import make_plan
from . import integrations as api

def register(request):
    form=UserCreationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        user=form.save(); Profile.objects.create(user=user); login(request,user); return redirect('dashboard')
    return render(request,'form.html',{'form':form,'title':'Create your account'})
@login_required
def dashboard(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    tasks=Task.objects.filter(user=request.user,completed=False)
    plan=make_plan(tasks,profile.bedtime)
    return render(request,'dashboard.html',{'plan':plan,'profile':profile,'completed':Task.objects.filter(user=request.user,completed=True),'checklist':ChecklistItem.objects.filter(user=request.user),'checkform':ChecklistForm(),'sleep':SleepEntry.objects.filter(user=request.user).order_by('-slept_at'),'google_enabled':bool(os.environ.get('GOOGLE_CLIENT_ID'))})

def _sync_saved_task(request,task):
    token=request.session.get('google_access_token')
    if not token or task.completed:
        return
    profile,_=Profile.objects.get_or_create(user=request.user)
    plan=make_plan(Task.objects.filter(user=request.user,completed=False),profile.bedtime)
    row=next((row for row in plan['tonight'] if row['task'].pk==task.pk),None)
    if not row:
        messages.info(request,'Task saved locally. It is not in tonight\'s plan, so no Google Calendar event was created.')
        return
    try:
        event=api.sync_calendar_event(token,task,row['start'],row['end'])
        task.google_event_id=event['id']
        task.save(update_fields=['google_event_id'])
        messages.success(request,'Task saved and synced to Google Calendar.')
    except (api.IntegrationError,KeyError):
        messages.warning(request,'Task saved locally, but Google Calendar sync failed. Reconnect Google or use Sync plan.')

@login_required
def task_edit(request,pk=None):
    task=get_object_or_404(Task,pk=pk,user=request.user) if pk else None
    form=TaskForm(request.POST or None,instance=task)
    if request.method=='POST' and form.is_valid():
        obj=form.save(commit=False); obj.user=request.user; obj.save()
        if request.session.get('google_access_token') and not obj.completed:
            _sync_saved_task(request,obj)
        else:
            messages.success(request,'Task saved.')
        return redirect('dashboard')
    return render(request,'form.html',{'form':form,'title':'Edit task' if pk else 'Add a task'})
@login_required
@require_POST
def task_delete(request,pk):
    get_object_or_404(Task,pk=pk,user=request.user).delete(); return redirect('dashboard')
@login_required
@require_POST
def task_toggle(request,pk):
    task=get_object_or_404(Task,pk=pk,user=request.user); task.completed=not task.completed; task.save(update_fields=['completed']); return redirect('dashboard')
@login_required
def profile_edit(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    form=ProfileForm(request.POST or None,instance=profile)
    if request.method=='POST' and form.is_valid():
        form.save(); return redirect('dashboard')
    return render(request,'form.html',{'form':form,'title':'Your routine and location','email_edit':True})
@login_required
@require_POST
def city_lookup(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    try:
        place=api.geocode_city(request.POST.get('city_query',''))
        parts=[place.get('name'),place.get('admin1'),place.get('country')]
        profile.city=', '.join(dict.fromkeys(part for part in parts if part))
        profile.latitude=place['latitude']; profile.longitude=place['longitude']
        profile.country_code=(place.get('country_code') or profile.country_code).upper()
        profile.save(update_fields=['city','country_code','latitude','longitude'])
        messages.success(request,f"Location updated to {profile.city}.")
    except api.IntegrationError as exc:
        messages.error(request,str(exc))
    return redirect('profile')
@login_required
@require_POST
def email_edit(request):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        value=request.POST.get('email',''); validate_email(value)
        request.user.email=value; request.user.save(update_fields=['email']); messages.success(request,'Email saved.')
    except ValidationError: messages.error(request,'Enter a valid email address.')
    return redirect('profile')
@login_required
def sleep_add(request):
    form=SleepForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        entry=form.save(commit=False); entry.user=request.user; entry.save(); return redirect('dashboard')
    return render(request,'form.html',{'form':form,'title':'Record your sleep'})
@login_required
@require_POST
def sleep_delete(request,pk):
    get_object_or_404(SleepEntry,pk=pk,user=request.user).delete(); return redirect('dashboard')
@login_required
@require_POST
def checklist_add(request):
    form=ChecklistForm(request.POST)
    if form.is_valid():
        item=form.save(commit=False); item.user=request.user; item.save()
    else: messages.error(request,'Enter a checklist item, up to 120 characters.')
    return redirect('dashboard')
@login_required
@require_POST
def checklist_action(request,pk,action):
    item=get_object_or_404(ChecklistItem,pk=pk,user=request.user)
    if action=='delete': item.delete()
    elif action=='toggle': item.packed=not item.packed; item.save(update_fields=['packed'])
    return redirect('dashboard')
@login_required
@require_POST
def photo_upload(request,pk):
    task=get_object_or_404(Task,pk=pk,user=request.user); file=request.FILES.get('photo')
    allowed_extensions={'.jpg','.jpeg','.png','.webp'}
    if not file or file.size>5*1024*1024 or file.content_type not in ['image/jpeg','image/png','image/webp'] or Path(file.name).suffix.lower() not in allowed_extensions:
        messages.error(request,'Choose a JPEG, PNG, or WebP image under 5 MB.'); return redirect('dashboard')
    task.photo_url=file; task.save(update_fields=['photo_url']); messages.success(request,'Photo stored locally.')
    return redirect('dashboard')
@login_required
def plan_print(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    plan=make_plan(Task.objects.filter(user=request.user,completed=False),profile.bedtime)
    return render(request,'plan_print.html',{'plan':plan})
def _plan_text(plan):
    tonight='\n'.join(f"- {row['start']:%I:%M %p}–{row['end']:%I:%M %p}: {row['task'].title} ({row['task'].minutes} minutes)" for row in plan['tonight']) or '- No tasks scheduled.'
    later='\n'.join(f"- {row['task'].title}: {row['reason']}" for row in plan['later']) or '- None.'
    return f"BeforeBed plan\nBedtime target: {plan['target']:%A, %B %d at %I:%M %p}\n\nTonight\n{tonight}\n\nNeeds a decision\n{later}\n"
@login_required
def plan_download(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    plan=make_plan(Task.objects.filter(user=request.user,completed=False),profile.bedtime)
    response=HttpResponse(_plan_text(plan),content_type='text/plain; charset=utf-8')
    response['Content-Disposition']='attachment; filename="beforebed-plan.txt"'
    return response
def _ics_escape(value):
    return str(value).replace('\\','\\\\').replace('\n','\\n').replace(',','\\,').replace(';','\\;')
def _ics_time(value):
    return value.astimezone(datetime_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
@login_required
def plan_calendar(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    plan=make_plan(Task.objects.filter(user=request.user,completed=False),profile.bedtime)
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//BeforeBed//Evening Planner//EN','CALSCALE:GREGORIAN']
    stamp=_ics_time(timezone.now())
    for row in plan['tonight']:
        task=row['task']
        lines += ['BEGIN:VEVENT',f'UID:task-{task.pk}-{row["start"]:%Y%m%d}@beforebed',f'DTSTAMP:{stamp}',f'DTSTART:{_ics_time(row["start"])}',f'DTEND:{_ics_time(row["end"])}',f'SUMMARY:{_ics_escape(task.title)}',f'DESCRIPTION:{_ics_escape("Planned by BeforeBed. Due " + task.deadline.isoformat())}','END:VEVENT']
    lines.append('END:VCALENDAR')
    response=HttpResponse('\r\n'.join(lines)+'\r\n',content_type='text/calendar; charset=utf-8')
    response['Content-Disposition']='attachment; filename="beforebed-plan.ics"'
    return response
@login_required
def weather(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    try:
        daily=api.weather(profile); rows=list(zip(daily['time'],daily['temperature_2m_max'],daily['precipitation_probability_max']))
        return render(request,'weather.html',{'rows':rows,'profile':profile})
    except (api.IntegrationError,KeyError):
        messages.error(request,'Weather is unavailable. Your tasks and checklist still work.'); return redirect('dashboard')

@login_required
def day_context(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    now=timezone.localtime()
    holidays=[]; errors=[]
    try:
        cutoff=now.date()+timedelta(days=60)
        holidays=[item for item in api.public_holidays(profile.country_code,now.year) if now.date() <= datetime.fromisoformat(item['date']).date() <= cutoff]
        if cutoff.year!=now.year:
            holidays += [item for item in api.public_holidays(profile.country_code,cutoff.year) if now.date() <= datetime.fromisoformat(item['date']).date() <= cutoff]
        holidays.sort(key=lambda item:item['date'])
        for holiday in holidays:
            holiday['date_value']=datetime.fromisoformat(holiday['date']).date()
            holiday['days_until']=(holiday['date_value']-now.date()).days
    except (api.IntegrationError,KeyError,ValueError) as exc:
        errors.append(str(exc) if isinstance(exc,api.IntegrationError) else 'Public holidays returned an unexpected response.')
    return render(request,'day_context.html',{'profile':profile,'holidays':holidays,'errors':errors})

@login_required
@require_POST
def reminder_test(request):
    if not request.user.email:
        messages.error(request,'Save your email address under My routine before sending a reminder.')
        return redirect('profile')
    profile,_=Profile.objects.get_or_create(user=request.user)
    plan=make_plan(Task.objects.filter(user=request.user,completed=False),profile.bedtime)
    body=_plan_text(plan)+'\nThis is a test reminder from BeforeBed.'
    try:
        api.send_email(request.user.email,'BeforeBed test reminder',body)
        messages.success(request,f'A test reminder was sent to {request.user.email}.')
    except api.IntegrationError as exc:
        messages.error(request,str(exc))
    return redirect('dashboard')
from datetime import datetime

@login_required
def calendar(request):
    token = request.session.get('google_access_token')
    if not token: 
        messages.info(request, 'Connect Google to view your calendar.')
        return redirect('google_start')
        
    try: 
        events = api.calendar_events(token)
        # Parse Google's ISO strings into Python datetime/date objects
        for event in events:
            if 'dateTime' in event.get('start', {}):
                event['start']['dateTime'] = datetime.fromisoformat(
                    event['start']['dateTime'].replace('Z', '+00:00')
                )
            elif 'date' in event.get('start', {}):
                event['start']['date'] = datetime.strptime(
                    event['start']['date'], '%Y-%m-%d'
                ).date()
    except api.IntegrationError as exc: 
        messages.error(request, str(exc))
        return redirect('dashboard')
        
    return render(request, 'calendar.html', {'events': events})
@login_required
@require_POST
def calendar_sync(request):
    token=request.session.get('google_access_token')
    if not token:
        messages.info(request,'Connect Google before syncing your plan.'); return redirect('google_start')
    profile,_=Profile.objects.get_or_create(user=request.user)
    plan=make_plan(Task.objects.filter(user=request.user,completed=False),profile.bedtime)
    if not plan['tonight']:
        messages.info(request,'No incomplete tasks currently fit in tonight’s plan, so there is nothing to sync.')
        return redirect('dashboard')
    synced=0
    try:
        for row in plan['tonight']:
            task=row['task']
            event=api.sync_calendar_event(token,task,row['start'],row['end'])
            task.google_event_id=event['id']; task.save(update_fields=['google_event_id'])
            synced+=1
        messages.success(request,f'{synced} task event(s) synced to Google Calendar.')
    except (api.IntegrationError,KeyError):
        messages.error(request,'Calendar sync needs edit permission. Click Connect Google again and approve Calendar access.')
    return redirect('dashboard')
def google_start(request):
    try:
        state=secrets.token_urlsafe(32); request.session['oauth_state']=state
        query=urllib.parse.urlencode({'client_id':api.required('GOOGLE_CLIENT_ID'),'redirect_uri':api.required('GOOGLE_REDIRECT_URI'),'response_type':'code','scope':'openid email profile https://www.googleapis.com/auth/calendar.events','state':state,'prompt':'consent','include_granted_scopes':'true'})
        return redirect('https://accounts.google.com/o/oauth2/v2/auth?'+query)
    except api.IntegrationError as exc: messages.error(request,str(exc)); return redirect('login')
def google_callback(request):
    expected=request.session.pop('oauth_state',None)
    if not expected or not secrets.compare_digest(expected,request.GET.get('state','')) or not request.GET.get('code'):
        messages.error(request,'Google authorization was cancelled or invalid.'); return redirect('login')
    try:
        data=urllib.parse.urlencode({'code':request.GET['code'],'client_id':api.required('GOOGLE_CLIENT_ID'),'client_secret':api.required('GOOGLE_CLIENT_SECRET'),'redirect_uri':api.required('GOOGLE_REDIRECT_URI'),'grant_type':'authorization_code'}).encode()
        token=api.call('https://oauth2.googleapis.com/token',data,{'Content-Type':'application/x-www-form-urlencoded'})['access_token']
        identity=api.call('https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+token})
        if not identity.get('email_verified'): raise api.IntegrationError('Google email must be verified.')
        subject=identity['sub']; linked=Profile.objects.filter(google_subject=subject).first()
        if request.user.is_authenticated:
            profile,_=Profile.objects.get_or_create(user=request.user)
            if linked and linked.user_id!=request.user.pk: raise api.IntegrationError('This Google account is already linked to another user.')
            if profile.google_subject and profile.google_subject!=subject: raise api.IntegrationError('A different Google account is already linked.')
            profile.google_subject=subject; profile.save(); user=request.user
        elif linked: user=linked.user
        else:
            user=get_user_model().objects.create_user(username='g_'+secrets.token_hex(12),email=identity['email'],password=None)
            Profile.objects.create(user=user,google_subject=subject)
        if not user.is_active: raise api.IntegrationError('This account is inactive.')
        login(request,user); request.session['google_access_token']=token
        messages.success(request,'Google connected. Calendar access lasts until the token expires; reconnect when needed.')
        return redirect('dashboard')
    except (api.IntegrationError,KeyError) as exc:
        messages.error(request,str(exc) if isinstance(exc,api.IntegrationError) else 'Google returned an unexpected response.'); return redirect('login')
@user_passes_test(lambda user:user.is_active and user.is_staff)
def staff_dashboard(request):
    return render(request,'staff.html',{'users':get_user_model().objects.count(),'tasks':Task.objects.count(),'complete':Task.objects.filter(completed=True).count(),'entries':SleepEntry.objects.count()})
