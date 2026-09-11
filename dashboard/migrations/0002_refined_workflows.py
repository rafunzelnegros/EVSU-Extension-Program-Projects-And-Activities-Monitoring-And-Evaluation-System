from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='fieldvisitlog',
            name='partner_representative_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='fieldvisitlog',
            name='partner_representative_postnominals',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='quarterlymonitoringreport',
            name='approved_vp_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='quarterlymonitoringreport',
            name='noted_dean_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='quarterlymonitoringreport',
            name='noted_extension_director_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AlterField(
            model_name='quarterlymonitoringreport',
            name='phase',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Phase 1'), (2, 'Phase 2'), (3, 'Phase 3'), (4, 'Phase 4'), (5, 'Phase 5'), (6, 'Phase 6'), (7, 'Phase 7')], null=True),
        ),
        migrations.AlterField(
            model_name='quarterlymonitoringreport',
            name='project_status',
            field=models.CharField(blank=True, choices=[('', 'Select status'), ('ONGOING', 'Ongoing'), ('INACTIVE', 'Inactive'), ('TERMINATED', 'Terminated')], default='', max_length=12),
        ),
        migrations.AlterModelOptions(
            name='fieldvisitlog',
            options={'ordering': ['-updated_at', '-year', '-quarter', 'project__title']},
        ),
    ]
