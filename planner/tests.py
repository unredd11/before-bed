from datetime import timedelta,time
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import Task,Profile
from .planning import make_plan
from .forms import SleepForm
from .integrations import IntegrationError
class BeforeBedTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('student',password='SecurePass123!')
        self.other=get_user_model().objects.create_user('other',password='SecurePass123!')
        self.client.force_login(self.user)
        self.task=Task.objects.create(user=self.user,title='Prepare slides',deadline=timezone.now()+timedelta(days=2),minutes=30)
    def test_dashboard_and_forms_render(self):
        for name in ['dashboard','task_add','profile','sleep_add']:
            self.assertEqual(self.client.get(reverse(name)).status_code,200)
        self.assertContains(self.client.get(reverse('dashboard')),'Prepare slides')
    def test_private_records(self):
        self.client.force_login(self.other)
        for name in ['task_delete','task_toggle','photo']:
            self.assertEqual(self.client.post(reverse(name,args=[self.task.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse('task_edit',args=[self.task.pk])).status_code,404)
        self.assertNotContains(self.client.get(reverse('dashboard')),'Prepare slides')
    def test_crud(self):
        data={'title':'Pack documents','deadline':(timezone.localtime()+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),'minutes':15,'priority':1}
        self.assertEqual(self.client.post(reverse('task_add'),data).status_code,302)
        task=Task.objects.get(title='Pack documents')
        data['title']='Pack uniform'
        self.client.post(reverse('task_edit',args=[task.pk]),data)
        task.refresh_from_db(); self.assertEqual(task.title,'Pack uniform')
        self.client.post(reverse('task_delete',args=[task.pk])); self.assertFalse(Task.objects.filter(pk=task.pk).exists())
    def test_mutations_require_post(self):
        self.assertEqual(self.client.get(reverse('task_delete',args=[self.task.pk])).status_code,405)
    def test_csrf_protected(self):
        client=Client(enforce_csrf_checks=True); client.force_login(self.user)
        self.assertEqual(client.post(reverse('task_delete',args=[self.task.pk])).status_code,403)
    def test_regular_user_cannot_open_staff_summary(self):
        self.assertEqual(self.client.get(reverse('staff_dashboard')).status_code,302)
        self.user.is_staff=True; self.user.save()
        self.assertEqual(self.client.get(reverse('staff_dashboard')).status_code,200)
    def test_plan_crosses_midnight_and_does_not_overbook(self):
        now=timezone.localtime().replace(hour=23,minute=30,second=0,microsecond=0)
        self.task.deadline=now+timedelta(hours=4); self.task.minutes=45
        second=Task(user=self.user,title='Too long',deadline=now+timedelta(hours=5),minutes=30)
        plan=make_plan([self.task,second],time(0,30),now)
        self.assertEqual(plan['target'].date(),(now+timedelta(days=1)).date())
        self.assertEqual(len(plan['tonight']),1); self.assertEqual(len(plan['later']),1)
        self.assertEqual(plan['remaining'],15)
    def test_expired_deadline_is_not_scheduled(self):
        self.task.deadline=timezone.now()-timedelta(hours=1)
        plan=make_plan([self.task],time(0,30))
        self.assertFalse(plan['tonight']); self.assertEqual(plan['later'][0]['reason'],'Deadline has passed.')
    def test_sleep_validation(self):
        now=timezone.localtime()
        self.assertFalse(SleepForm({'slept_at':now.isoformat(),'woke_at':(now-timedelta(hours=1)).isoformat()}).is_valid())
        self.assertTrue(SleepForm({'slept_at':now.isoformat(),'woke_at':(now+timedelta(hours=7)).isoformat()}).is_valid())
    @patch('planner.integrations.weather',side_effect=IntegrationError('offline'))
    def test_weather_failure_keeps_app_working(self,mock):
        self.assertRedirects(self.client.get(reverse('weather')),reverse('dashboard'))
    @patch('planner.integrations.weather',return_value={'time':['2026-10-15'],'temperature_2m_max':[28],'precipitation_probability_max':[60]})
    def test_weather_success(self,mock):
        self.assertContains(self.client.get(reverse('weather')),'60%')
    @patch('planner.integrations.geocode_city',return_value={'name':'Taipei','admin1':'Taiwan','country':'Taiwan','country_code':'TW','latitude':25.0478,'longitude':121.5319})
    def test_city_lookup_updates_weather_coordinates(self,mock):
        response=self.client.post(reverse('city_lookup'),{'city_query':'Taipei, Taiwan'})
        self.assertRedirects(response,reverse('profile'))
        profile=Profile.objects.get(user=self.user)
        self.assertEqual(profile.city,'Taipei, Taiwan')
        self.assertEqual(profile.latitude,25.0478)
        self.assertEqual(profile.longitude,121.5319)
        self.assertEqual(profile.country_code,'TW')
        mock.assert_called_once_with('Taipei, Taiwan')
    @patch('planner.integrations.geocode_city',side_effect=IntegrationError('No matching city was found.'))
    def test_city_lookup_failure_keeps_saved_location(self,mock):
        profile=Profile.objects.create(user=self.user,city='Existing City',latitude=1,longitude=2)
        self.client.post(reverse('city_lookup'),{'city_query':'Unknown'})
        profile.refresh_from_db()
        self.assertEqual(profile.city,'Existing City')
    def test_plan_downloads(self):
        profile,_=Profile.objects.get_or_create(user=self.user)
        profile.bedtime=(timezone.localtime()+timedelta(hours=2)).time()
        profile.save(update_fields=['bedtime'])
        text_response=self.client.get(reverse('plan_download'))
        self.assertEqual(text_response.status_code,200)
        self.assertEqual(text_response['Content-Type'],'text/plain; charset=utf-8')
        self.assertContains(text_response,'Prepare slides')
        calendar_response=self.client.get(reverse('plan_calendar'))
        self.assertEqual(calendar_response.status_code,200)
        self.assertIn('text/calendar',calendar_response['Content-Type'])
        self.assertContains(calendar_response,'BEGIN:VCALENDAR')
        self.assertContains(calendar_response,'SUMMARY:Prepare slides')
        self.assertContains(self.client.get(reverse('plan_print')),'Print this plan')
    def test_photo_is_stored_locally_and_deleted_with_task(self):
        media_root=settings.BASE_DIR/'test_media'
        with override_settings(MEDIA_ROOT=media_root):
            photo=SimpleUploadedFile('notes.png',b'example image bytes',content_type='image/png')
            self.client.post(reverse('photo',args=[self.task.pk]),{'photo':photo})
            self.task.refresh_from_db()
            self.assertTrue(self.task.photo_url.name.startswith('task_photos/'))
            storage=self.task.photo_url.storage; name=self.task.photo_url.name
            self.assertTrue(storage.exists(name))
            self.task.delete()
            self.assertFalse(storage.exists(name))
    def test_oauth_rejects_invalid_state(self):
        self.assertRedirects(self.client.get(reverse('google_callback'),{'state':'bad','code':'bad'}),reverse('login'))
    @patch('planner.integrations.sync_calendar_event',return_value={'id':'google-event-123'})
    def test_calendar_sync_creates_and_remembers_event(self,sync_mock):
        profile,_=Profile.objects.get_or_create(user=self.user)
        profile.bedtime=(timezone.localtime()+timedelta(hours=2)).time()
        profile.save(update_fields=['bedtime'])
        session=self.client.session; session['google_access_token']='token'; session.save()
        response=self.client.post(reverse('calendar_sync'))
        self.assertRedirects(response,reverse('dashboard'))
        self.task.refresh_from_db()
        self.assertEqual(self.task.google_event_id,'google-event-123')
        sync_mock.assert_called_once()
    @patch('planner.integrations.public_holidays',return_value=[])
    def test_day_context_uses_holiday_api(self,holiday_mock):
        response=self.client.get(reverse('day_context'))
        self.assertEqual(response.status_code,200)
        holiday_mock.assert_called()
    @patch('planner.integrations.send_email',return_value={'id':'email-id'})
    def test_resend_test_reminder(self,email_mock):
        self.user.email='student@example.com'; self.user.save(update_fields=['email'])
        response=self.client.post(reverse('reminder_test'))
        self.assertRedirects(response,reverse('dashboard'))
        email_mock.assert_called_once()
        self.assertEqual(email_mock.call_args.args[0],'student@example.com')
    def test_registration(self):
        self.client.logout()
        response=self.client.post(reverse('register'),{'username':'newstudent','password1':'DifferentSecure482!','password2':'DifferentSecure482!'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(Profile.objects.filter(user__username='newstudent').exists())
