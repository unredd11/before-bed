from datetime import timedelta,time
from unittest.mock import patch
from django.test import TestCase,Client
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
    @patch('planner.integrations.send_plan',return_value={'id':'example'})
    def test_email_sends_current_user_plan(self,mock):
        self.user.email='student@example.com'; self.user.save()
        self.client.post(reverse('plan_email'))
        self.assertEqual(mock.call_args.args[0],'student@example.com')
        self.assertIn('Prepare slides',mock.call_args.args[1])
    def test_oauth_rejects_invalid_state(self):
        self.assertRedirects(self.client.get(reverse('google_callback'),{'state':'bad','code':'bad'}),reverse('login'))
    def test_registration(self):
        self.client.logout()
        response=self.client.post(reverse('register'),{'username':'newstudent','password1':'DifferentSecure482!','password2':'DifferentSecure482!'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(Profile.objects.filter(user__username='newstudent').exists())
