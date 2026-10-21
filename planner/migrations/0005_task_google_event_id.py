from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('planner', '0004_profile_country_code')]

    operations = [
        migrations.AddField(
            model_name='task',
            name='google_event_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
