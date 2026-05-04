from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_farmerprofile_phone_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farmerprofile',
            name='preferred_language',
            field=models.CharField(
                choices=[
                    ('en', 'English'),
                    ('ha', 'Hausa'),
                    ('ig', 'Igbo'),
                    ('yo', 'Yoruba'),
                ],
                default='en',
                max_length=5,
            ),
        ),
    ]
