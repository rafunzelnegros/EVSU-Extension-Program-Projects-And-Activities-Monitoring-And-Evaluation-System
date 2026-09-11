from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_sdgs(apps, schema_editor):
    PPA = apps.get_model('dashboard', 'PPA')
    SDG = apps.get_model('dashboard', 'SustainableDevelopmentGoal')
    for ppa in PPA.objects.exclude(sdgs=''):
        text = (ppa.sdgs or '').strip()
        if text and not SDG.objects.filter(ppa_id=ppa.pk).exists():
            SDG.objects.create(ppa_id=ppa.pk, order=1, goal_description=text)


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0002_refined_workflows')]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='post_nominals',
            field=models.CharField(blank=True, help_text='Optional post-nominal letters, e.g. PhD, MPA, RN', max_length=120),
        ),
        migrations.AddField(
            model_name='quarterlymonitoringreport',
            name='school_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='quarterlymonitoringreport',
            name='campus_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='quarterlymonitoringreport',
            name='department',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.CreateModel(
            name='SustainableDevelopmentGoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=1)),
                ('goal_description', models.CharField(max_length=300)),
                ('target', models.CharField(blank=True, max_length=300)),
                ('description', models.TextField(blank=True)),
                ('indicator', models.CharField(blank=True, max_length=300)),
                ('ppa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sdg_entries', to='dashboard.ppa')),
            ],
            options={'ordering': ['order', 'id']},
        ),
        migrations.RunPython(migrate_legacy_sdgs, migrations.RunPython.noop),
    ]
