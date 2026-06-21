from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('declarations', '0002_alter_declaration_document_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentFound',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('found_by', models.CharField(blank=True, max_length=200, verbose_name='Trouvé par')),
                ('found_at', models.DateField(default=django.utils.timezone.now, verbose_name='Date de découverte')),
                ('found_location', models.CharField(blank=True, max_length=300, verbose_name='Lieu de découverte')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('status', models.CharField(choices=[('pending', 'En attente de récupération'), ('notified', 'Citoyen notifié'), ('collected', 'Document récupéré'), ('unclaimed', 'Non réclamé — archivé')], default='pending', max_length=20, verbose_name='Statut')),
                ('collection_deadline', models.DateField(blank=True, null=True, verbose_name='Date limite de récupération')),
                ('collected_at', models.DateTimeField(blank=True, null=True, verbose_name='Récupéré le')),
                ('notified_at', models.DateTimeField(blank=True, null=True, verbose_name='Citoyen notifié le')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('declaration', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='found_record', to='declarations.declaration', verbose_name='Déclaration')),
                ('registered_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='found_documents', to=settings.AUTH_USER_MODEL, verbose_name='Enregistré par')),
            ],
            options={
                'verbose_name': 'Document retrouvé',
                'verbose_name_plural': 'Documents retrouvés',
                'ordering': ['-created_at'],
            },
        ),
    ]
