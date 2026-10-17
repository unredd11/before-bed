from datetime import time
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
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
    photo_url=models.FileField(upload_to='task_photos/',blank=True,validators=[FileExtensionValidator(['jpg','jpeg','png','webp'])])
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

@receiver(post_delete,sender=Task)
def delete_task_photo(sender,instance,**kwargs):
    if instance.photo_url:
        instance.photo_url.delete(save=False)

@receiver(pre_save,sender=Task)
def delete_replaced_task_photo(sender,instance,**kwargs):
    if not instance.pk:
        return
    old=Task.objects.filter(pk=instance.pk).only('photo_url').first()
    if old and old.photo_url and old.photo_url.name!=getattr(instance.photo_url,'name',''):
        old.photo_url.delete(save=False)
