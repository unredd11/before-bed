from datetime import time
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
class Profile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    bedtime=models.TimeField(default=time(0,30))
    city=models.CharField(max_length=80,blank=True)
    latitude=models.FloatField(default=1.3521,validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude=models.FloatField(default=103.8198,validators=[MinValueValidator(-180),MaxValueValidator(180)])
    google_subject=models.CharField(max_length=255,unique=True,null=True,blank=True)
class Task(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    title=models.CharField(max_length=120)
    deadline=models.DateTimeField()
    minutes=models.PositiveIntegerField(default=30,validators=[MinValueValidator(1),MaxValueValidator(720)])
    priority=models.IntegerField(choices=[(1,'High'),(2,'Medium'),(3,'Low')],default=2)
    completed=models.BooleanField(default=False)
    photo_url=models.URLField(blank=True)
    def __str__(self): return self.title
class ChecklistItem(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    label=models.CharField(max_length=120)
    packed=models.BooleanField(default=False)
class SleepEntry(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    slept_at=models.DateTimeField()
    woke_at=models.DateTimeField()
    @property
    def hours(self): return round((self.woke_at-self.slept_at).total_seconds()/3600,1)
