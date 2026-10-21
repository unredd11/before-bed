from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('planner', '0003_local_task_photos')]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='country_code',
            field=models.CharField(default='SG', max_length=2),
        ),
    ]
