import os,secrets,urllib.parse,json
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
    return render(request,'dashboard.html',{'plan':plan,'profile':profile,'completed':Task.objects.filter(user=request.user,completed=True),'checklist':ChecklistItem.objects.filter(user=request.user),'checkform':ChecklistForm(),'sleep':SleepEntry.objects.filter(user=request.user).order_by('-slept_at')[:7],'google_enabled':bool(os.environ.get('GOOGLE_CLIENT_ID'))})
@login_required
def task_edit(request,pk=None):
    task=get_object_or_404(Task,pk=pk,user=request.user) if pk else None
    form=TaskForm(request.POST or None,instance=task)
    if request.method=='POST' and form.is_valid():
        obj=form.save(commit=False); obj.user=request.user; obj.save(); messages.success(request,'Task saved.'); return redirect('dashboard')
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
    if not file or file.size>5*1024*1024 or file.content_type not in ['image/jpeg','image/png','image/webp']:
        messages.error(request,'Choose a JPEG, PNG, or WebP image under 5 MB.'); return redirect('dashboard')
    try: task.photo_url=api.upload_photo(file); task.save(update_fields=['photo_url']); messages.success(request,'Photo attached.')
    except api.IntegrationError as exc: messages.error(request,str(exc))
    return redirect('dashboard')
@login_required
@require_POST
def plan_email(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    plan=make_plan(Task.objects.filter(user=request.user,completed=False),profile.bedtime)
    body='Bedtime target: '+str(plan['target'])+'\n\nTonight:\n'+'\n'.join(f"{row['task'].title} ({row['task'].minutes} minutes)" for row in plan['tonight'])+'\n\nNeeds a decision:\n'+'\n'.join(f"{row['task'].title}: {row['reason']}" for row in plan['later'])
    try: api.send_plan(request.user.email,body); messages.success(request,'Plan sent to your email.')
    except api.IntegrationError as exc: messages.error(request,str(exc))
    return redirect('dashboard')
@login_required
def weather(request):
    profile,_=Profile.objects.get_or_create(user=request.user)
    try:
        daily=api.weather(profile); rows=list(zip(daily['time'],daily['temperature_2m_max'],daily['precipitation_probability_max']))
        return render(request,'weather.html',{'rows':rows,'profile':profile})
    except (api.IntegrationError,KeyError):
        messages.error(request,'Weather is unavailable. Your tasks and checklist still work.'); return redirect('dashboard')
@login_required
def calendar(request):
    token=request.session.get('google_access_token')
    if not token: messages.info(request,'Connect Google to view your calendar.'); return redirect('google_start')
    try: events=api.calendar_events(token)
    except api.IntegrationError as exc: messages.error(request,str(exc)); return redirect('dashboard')
    return render(request,'calendar.html',{'events':events})
def google_start(request):
    try:
        state=secrets.token_urlsafe(32); request.session['oauth_state']=state
        query=urllib.parse.urlencode({'client_id':api.required('GOOGLE_CLIENT_ID'),'redirect_uri':api.required('GOOGLE_REDIRECT_URI'),'response_type':'code','scope':'openid email profile https://www.googleapis.com/auth/calendar.events.readonly','state':state,'prompt':'consent'})
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
