from datetime import datetime,timedelta
from django.utils import timezone
def make_plan(tasks,bedtime,now=None):
    now=timezone.localtime(now or timezone.now())
    target=timezone.make_aware(datetime.combine(now.date(),bedtime),now.tzinfo)
    if target<=now: target+=timedelta(days=1)
    budget=max(0,int((target-now).total_seconds()/60))
    cursor=now
    tonight=[]; later=[]
    for task in sorted(tasks,key=lambda t:(t.deadline,t.priority,t.pk or 0)):
        end=cursor+timedelta(minutes=task.minutes)
        if task.minutes<=budget and end<=task.deadline:
            tonight.append({'task':task,'start':cursor,'end':end})
            cursor=end; budget-=task.minutes
        else:
            reason='Deadline has passed.' if task.deadline<=now else ('Cannot finish before its deadline.' if end>task.deadline else 'Does not fit before your bedtime target.')
            later.append({'task':task,'reason':reason})
    return {'target':target,'tonight':tonight,'later':later,'remaining':budget}
