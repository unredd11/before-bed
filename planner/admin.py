from django.contrib import admin
from .models import Task,Profile,SleepEntry,ChecklistItem
admin.site.register([Task,Profile,SleepEntry,ChecklistItem])
admin.site.site_header='BeforeBed Administration'
