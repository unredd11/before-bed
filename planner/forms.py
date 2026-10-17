from django import forms
from .models import Task,Profile,SleepEntry,ChecklistItem
class TaskForm(forms.ModelForm):
    class Meta:
        model=Task
        fields=['title','deadline','minutes','priority','completed']
        widgets={'deadline':forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'})}
class ProfileForm(forms.ModelForm):
    class Meta:
        model=Profile
        fields=['bedtime','city','latitude','longitude']
        widgets={'bedtime':forms.TimeInput(attrs={'type':'time'})}
class SleepForm(forms.ModelForm):
    class Meta:
        model=SleepEntry
        fields=['slept_at','woke_at']
        widgets={f:forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'}) for f in fields}
    def clean(self):
        data=super().clean()
        if data.get('slept_at') and data.get('woke_at'):
            hours=(data['woke_at']-data['slept_at']).total_seconds()/3600
            if not 0<hours<=24: raise forms.ValidationError('Wake-up must be after bedtime and within 24 hours.')
        return data
class ChecklistForm(forms.ModelForm):
    class Meta:
        model=ChecklistItem
        fields=['label']
