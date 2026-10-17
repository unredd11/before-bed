from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [('planner', '0002_alter_profile_bedtime')]
    operations = [
        migrations.AlterField(
            model_name='task',
            name='photo_url',
            field=models.FileField(
                blank=True,
                upload_to='task_photos/',
                validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
            ),
        ),
    ]
