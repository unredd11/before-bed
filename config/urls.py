from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth
from django.conf import settings
from django.conf.urls.static import static
from planner import views as v
urlpatterns=[
path('admin/',admin.site.urls),path('',v.dashboard,name='dashboard'),path('register/',v.register,name='register'),
path('login/',auth.LoginView.as_view(template_name='form.html',extra_context={'title':'Welcome back'}),name='login'),path('logout/',auth.LogoutView.as_view(),name='logout'),
path('tasks/new/',v.task_edit,name='task_add'),path('tasks/<int:pk>/edit/',v.task_edit,name='task_edit'),path('tasks/<int:pk>/delete/',v.task_delete,name='task_delete'),path('tasks/<int:pk>/toggle/',v.task_toggle,name='task_toggle'),path('tasks/<int:pk>/photo/',v.photo_upload,name='photo'),
path('routine/',v.profile_edit,name='profile'),path('routine/find-city/',v.city_lookup,name='city_lookup'),path('routine/email/',v.email_edit,name='email_edit'),path('sleep/new/',v.sleep_add,name='sleep_add'),path('sleep/<int:pk>/delete/',v.sleep_delete,name='sleep_delete'),
path('checklist/new/',v.checklist_add,name='checklist_add'),path('checklist/<int:pk>/<str:action>/',v.checklist_action,name='checklist_action'),
path('plan/print/',v.plan_print,name='plan_print'),path('plan/download/',v.plan_download,name='plan_download'),path('plan/calendar.ics',v.plan_calendar,name='plan_calendar'),path('weather/',v.weather,name='weather'),path('calendar/',v.calendar,name='calendar'),path('google/start/',v.google_start,name='google_start'),path('google/callback/',v.google_callback,name='google_callback'),path('overview/',v.staff_dashboard,name='staff_dashboard')]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
