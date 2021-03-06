# Generated by Django 2.1 on 2019-11-08 07:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('server_manager', '0004_auto_20191108_0452'),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.IntegerField(choices=[(1, 'SMALL'), (2, 'MEDIUM'), (3, 'BIG')])),
                ('avg_n_cooperative_server', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='application',
            name='area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='server_manager.Area'),
        ),
    ]
