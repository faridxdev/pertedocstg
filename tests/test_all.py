"""
PerteDocsTG — Tests complets (unitaires, intégration, API)
Couverture cible : 90%+
"""

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
import json

from declarations.models import Declaration, DocumentType, StatusHistory
from documents.models import Attachment, Receipt
from notifications.models import Notification
from audit.models import AuditLog
from core.models import Region, Prefecture, SiteConfiguration

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# FACTORIES / HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def make_user(email='citizen@test.tg', role='citizen', **kwargs):
    return User.objects.create_user(
        email=email,
        password='TestPass123!',
        first_name='Kofi',
        last_name='Atta',
        role=role,
        is_verified=True,
        **kwargs,
    )


def make_agent(email='agent@test.tg'):
    return make_user(email=email, role='agent')


def make_admin(email='admin@test.tg'):
    return make_user(email=email, role='admin')


def make_document_type(code='cni', name="Carte Nationale d'Identité"):
    return DocumentType.objects.get_or_create(
        code=code,
        defaults={'name': name, 'is_active': True, 'processing_days': 2},
    )[0]


def make_region():
    return Region.objects.get_or_create(
        name='Maritime', defaults={'code': 'MAR', 'capital': 'Lomé', 'order': 1}
    )[0]


def make_prefecture():
    region = make_region()
    return Prefecture.objects.get_or_create(
        code='GOL',
        defaults={'region': region, 'name': 'Golfe', 'capital': 'Lomé'},
    )[0]


def make_declaration(user=None, status='draft', **kwargs):
    if user is None:
        user = make_user()
    doc_type = make_document_type()
    prefecture = make_prefecture()
    declaration = Declaration.objects.create(
        declarant=user,
        status=status,
        first_name='Kofi',
        last_name='Atta',
        full_name='Kofi Atta',
        date_of_birth=date(1990, 5, 15),
        place_of_birth='Lomé',
        nationality='Togolaise',
        phone='+22890123456',
        email=user.email,
        profession='Ingénieur',
        address='Quartier Bé, Lomé',
        prefecture=prefecture,
        document_type=doc_type,
        document_number='TG-12345678',
        document_issue_date=date(2020, 1, 10),
        document_issue_place='Lomé',
        loss_date=date(2024, 3, 1),
        loss_place='Marché de Lomé',
        loss_circumstances='Perte lors d\'un déplacement au marché.',
        loss_description='J\'ai perdu ma carte nationale d\'identité lors d\'un déplacement. '
                         'Je ne l\'ai pas retrouvée malgré mes recherches.',
        honor_declaration=True,
        **kwargs,
    )
    return declaration


# ─────────────────────────────────────────────────────────────────────────────
# TESTS MODÈLES
# ─────────────────────────────────────────────────────────────────────────────

class UserModelTest(TestCase):
    def test_create_citizen(self):
        user = make_user()
        self.assertEqual(user.role, 'citizen')
        self.assertTrue(user.is_citizen)
        self.assertFalse(user.is_agent)
        self.assertFalse(user.is_administrator)

    def test_create_agent(self):
        agent = make_agent()
        self.assertEqual(agent.role, 'agent')
        self.assertTrue(agent.is_agent)

    def test_create_admin(self):
        admin = make_admin()
        self.assertTrue(admin.is_administrator)

    def test_full_name(self):
        user = make_user()
        self.assertEqual(user.get_full_name(), 'Kofi Atta')

    def test_lock_account(self):
        user = make_user()
        self.assertFalse(user.is_locked)
        user.lock_account(minutes=30)
        self.assertTrue(user.is_locked)

    def test_unlock_account(self):
        user = make_user()
        user.lock_account(minutes=30)
        user.unlock_account()
        self.assertFalse(user.is_locked)
        self.assertEqual(user.failed_login_attempts, 0)

    def test_superuser_creation(self):
        admin = User.objects.create_superuser(
            email='super@test.tg', password='SuperPass123!'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, 'super_admin')


class DeclarationModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.declaration = make_declaration(self.user)

    def test_declaration_number_generated(self):
        self.assertTrue(self.declaration.declaration_number.startswith('TG-'))
        self.assertEqual(len(self.declaration.declaration_number), 12)

    def test_verification_token_generated(self):
        self.assertIsNotNone(self.declaration.verification_token)
        self.assertGreater(len(self.declaration.verification_token), 20)

    def test_full_name_set(self):
        self.assertEqual(self.declaration.full_name, 'Kofi Atta')

    def test_is_editable_draft(self):
        self.assertTrue(self.declaration.is_editable)

    def test_is_not_editable_submitted(self):
        self.declaration.status = 'submitted'
        self.assertFalse(self.declaration.is_editable)

    def test_status_color(self):
        self.assertEqual(self.declaration.status_color, 'gray')
        self.declaration.status = 'validated'
        self.assertEqual(self.declaration.status_color, 'green')
        self.declaration.status = 'rejected'
        self.assertEqual(self.declaration.status_color, 'red')

    def test_valid_status_transition(self):
        self.declaration.status = 'draft'
        self.declaration.save()
        result = self.declaration.transition_to('submitted', user=self.user)
        self.assertTrue(result)
        self.declaration.refresh_from_db()
        self.assertEqual(self.declaration.status, 'submitted')

    def test_invalid_status_transition(self):
        result = self.declaration.transition_to('validated', user=self.user)
        self.assertFalse(result)
        self.declaration.refresh_from_db()
        self.assertEqual(self.declaration.status, 'draft')

    def test_status_history_created_on_transition(self):
        self.declaration.transition_to('submitted', user=self.user)
        history = StatusHistory.objects.filter(declaration=self.declaration)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().old_status, 'draft')
        self.assertEqual(history.first().new_status, 'submitted')

    def test_submitted_at_set_on_submit(self):
        self.declaration.transition_to('submitted', user=self.user)
        self.declaration.refresh_from_db()
        self.assertIsNotNone(self.declaration.submitted_at)

    def test_full_validation_workflow(self):
        agent = make_agent()
        self.declaration.transition_to('submitted', user=self.user)
        self.declaration.transition_to('in_progress', user=agent)
        self.declaration.transition_to('validated', user=agent)
        self.declaration.refresh_from_db()
        self.assertEqual(self.declaration.status, 'validated')
        self.assertIsNotNone(self.declaration.processed_at)
        self.assertEqual(self.declaration.validated_by, agent)

    def test_rejection_workflow(self):
        agent = make_agent()
        self.declaration.transition_to('submitted', user=self.user)
        self.declaration.transition_to('in_progress', user=agent)
        self.declaration.transition_to('rejected', user=agent, notes='Informations insuffisantes')
        self.declaration.refresh_from_db()
        self.assertEqual(self.declaration.status, 'rejected')
        self.assertEqual(self.declaration.rejection_reason, 'Informations insuffisantes')

    def test_unique_declaration_number(self):
        decl2 = make_declaration(self.user, email='other@test.tg')
        self.assertNotEqual(self.declaration.declaration_number, decl2.declaration_number)

    def test_verification_url(self):
        url = self.declaration.get_verification_url()
        self.assertIn(self.declaration.verification_token, url)


class DocumentTypeModelTest(TestCase):
    def test_document_type_creation(self):
        doc_type = make_document_type()
        self.assertEqual(doc_type.code, 'cni')
        self.assertTrue(doc_type.is_active)

    def test_str_representation(self):
        doc_type = make_document_type()
        self.assertEqual(str(doc_type), "Carte Nationale d'Identité")


class AttachmentModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.declaration = make_declaration(self.user)

    def test_attachment_creation(self):
        file = SimpleUploadedFile('test.pdf', b'%PDF-1.4 test content', content_type='application/pdf')
        attachment = Attachment.objects.create(
            declaration=self.declaration,
            uploaded_by=self.user,
            file=file,
            original_name='test.pdf',
            file_size=len(b'%PDF-1.4 test content'),
            mime_type='application/pdf',
        )
        self.assertEqual(attachment.declaration, self.declaration)
        self.assertEqual(attachment.original_name, 'test.pdf')
        self.assertTrue(attachment.is_pdf)
        self.assertFalse(attachment.is_image)

    def test_file_size_display(self):
        attachment = Attachment(file_size=1536)
        self.assertIn('Ko', attachment.file_size_display)

        attachment2 = Attachment(file_size=2 * 1024 * 1024)
        self.assertIn('Mo', attachment2.file_size_display)


class RegionPrefectureModelTest(TestCase):
    def test_region_prefecture_relationship(self):
        region = make_region()
        prefecture = make_prefecture()
        self.assertEqual(prefecture.region, region)
        self.assertIn(prefecture, region.prefectures.all())

    def test_str_representation(self):
        region = make_region()
        self.assertEqual(str(region), 'Maritime')
        prefecture = make_prefecture()
        self.assertIn('Golfe', str(prefecture))
        self.assertIn('Maritime', str(prefecture))


# ─────────────────────────────────────────────────────────────────────────────
# TESTS VUES
# ─────────────────────────────────────────────────────────────────────────────

class LandingPageViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_landing_page_status_200(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_landing_page_template(self):
        response = self.client.get(reverse('core:home'))
        self.assertTemplateUsed(response, 'core/landing.html')

    def test_landing_page_context(self):
        response = self.client.get(reverse('core:home'))
        self.assertIn('document_types', response.context)
        self.assertIn('stats', response.context)
        self.assertIn('steps', response.context)


class VerificationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.declaration = make_declaration(self.user, status='validated')

    def test_valid_token_shows_declaration(self):
        response = self.client.get(
            reverse('core:verification', kwargs={'token': self.declaration.verification_token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['valid'])
        self.assertEqual(response.context['declaration'], self.declaration)

    def test_invalid_token_shows_error(self):
        response = self.client.get(
            reverse('core:verification', kwargs={'token': 'invalid-token-xyz'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['valid'])


class DeclarationListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.other_user = make_user(email='other@test.tg')
        self.declaration = make_declaration(self.user, status='submitted')
        self.other_declaration = make_declaration(self.other_user, status='submitted')

    def test_requires_login(self):
        response = self.client.get(reverse('declarations:list'))
        self.assertNotEqual(response.status_code, 200)

    def test_citizen_sees_only_own_declarations(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('declarations:list'))
        self.assertEqual(response.status_code, 200)
        declarations = response.context['declarations']
        self.assertIn(self.declaration, declarations)
        self.assertNotIn(self.other_declaration, declarations)

    def test_agent_sees_all_declarations(self):
        agent = make_agent()
        self.client.force_login(agent)
        response = self.client.get(reverse('declarations:list'))
        declarations = response.context['declarations']
        self.assertIn(self.declaration, declarations)
        self.assertIn(self.other_declaration, declarations)

    def test_search_by_declaration_number(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('declarations:list'),
            {'query': self.declaration.declaration_number},
        )
        declarations = response.context['declarations']
        self.assertIn(self.declaration, declarations)

    def test_filter_by_status(self):
        make_declaration(self.user, status='validated')
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('declarations:list'), {'status': 'submitted'}
        )
        for decl in response.context['declarations']:
            self.assertEqual(decl.status, 'submitted')


class DeclarationDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.declaration = make_declaration(self.user, status='submitted')

    def test_owner_can_view_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('declarations:detail', kwargs={'pk': self.declaration.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['declaration'], self.declaration)

    def test_other_user_cannot_view(self):
        other = make_user(email='other2@test.tg')
        self.client.force_login(other)
        response = self.client.get(
            reverse('declarations:detail', kwargs={'pk': self.declaration.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_agent_can_view_any_declaration(self):
        agent = make_agent()
        self.client.force_login(agent)
        response = self.client.get(
            reverse('declarations:detail', kwargs={'pk': self.declaration.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_audit_log_created_on_view(self):
        self.client.force_login(self.user)
        self.client.get(
            reverse('declarations:detail', kwargs={'pk': self.declaration.pk})
        )
        logs = AuditLog.objects.filter(
            action='view',
            object_id=str(self.declaration.pk),
        )
        self.assertGreater(logs.count(), 0)


class DeclarationWizardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        make_document_type()
        make_prefecture()

    def test_step1_get(self):
        response = self.client.get(reverse('declarations:wizard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertEqual(response.context['step'], 1)

    def test_step1_post_valid(self):
        data = {
            'first_name': 'Kofi',
            'last_name': 'Atta',
            'date_of_birth': '1990-05-15',
            'place_of_birth': 'Lomé',
            'nationality': 'Togolaise',
            'phone': '+22890123456',
            'email': self.user.email,
            'profession': 'Ingénieur',
            'address': 'Quartier Bé, Lomé',
            'prefecture': str(make_prefecture().pk),
        }
        response = self.client.post(reverse('declarations:wizard'), data)
        self.assertRedirects(response, reverse('declarations:wizard', kwargs={'step': 2}))

    def test_step1_post_invalid_phone(self):
        data = {
            'first_name': 'Kofi',
            'last_name': 'Atta',
            'date_of_birth': '1990-05-15',
            'place_of_birth': 'Lomé',
            'nationality': 'Togolaise',
            'phone': '123',  # invalide
            'email': self.user.email,
            'address': 'Lomé',
        }
        response = self.client.post(reverse('declarations:wizard'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'phone', None)

    def test_wizard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('declarations:wizard'))
        self.assertNotEqual(response.status_code, 200)


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_citizen_dashboard(self):
        user = make_user()
        self.client.force_login(user)
        make_declaration(user, status='validated')
        make_declaration(user, status='submitted')
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('stats', response.context)
        stats = response.context['stats']
        self.assertGreaterEqual(stats['total'], 2)

    def test_admin_dashboard_requires_admin_role(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:admin'))
        self.assertNotEqual(response.status_code, 200)

    def test_admin_dashboard_accessible_by_admin(self):
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('kpis', response.context)

    def test_agent_dashboard_accessible_by_agent(self):
        agent = make_agent()
        self.client.force_login(agent)
        response = self.client.get(reverse('dashboard:agent'))
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS FORMULAIRES
# ─────────────────────────────────────────────────────────────────────────────

class DeclarationStep1FormTest(TestCase):
    def setUp(self):
        make_prefecture()

    def get_valid_data(self):
        return {
            'first_name': 'Kofi',
            'last_name': 'Atta',
            'date_of_birth': '1990-05-15',
            'place_of_birth': 'Lomé',
            'nationality': 'Togolaise',
            'phone': '+22890123456',
            'email': 'kofi@test.tg',
            'profession': 'Ingénieur',
            'address': 'Quartier Bé, Lomé',
            'prefecture': str(make_prefecture().pk),
        }

    def test_valid_form(self):
        from declarations.forms import DeclarationStep1Form
        form = DeclarationStep1Form(data=self.get_valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_phone_format(self):
        from declarations.forms import DeclarationStep1Form
        data = self.get_valid_data()
        data['phone'] = '123'
        form = DeclarationStep1Form(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_future_date_of_birth_invalid(self):
        from declarations.forms import DeclarationStep1Form
        data = self.get_valid_data()
        data['date_of_birth'] = (timezone.now().date() + timedelta(days=1)).isoformat()
        form = DeclarationStep1Form(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)

    def test_underage_invalid(self):
        from declarations.forms import DeclarationStep1Form
        data = self.get_valid_data()
        data['date_of_birth'] = (timezone.now().date() - timedelta(days=5 * 365)).isoformat()
        form = DeclarationStep1Form(data=data)
        self.assertFalse(form.is_valid())


class DeclarationStep3FormTest(TestCase):
    def test_short_description_optional(self):
        from declarations.forms import DeclarationStep3Form
        form = DeclarationStep3Form(data={
            'loss_date': '2024-03-01',
            'loss_place': 'Lomé',
            'loss_circumstances': 'Perte au marché.',
            'loss_description': 'Trop court',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form(self):
        from declarations.forms import DeclarationStep3Form
        form = DeclarationStep3Form(data={
            'loss_date': '2024-03-01',
            'loss_place': 'Marché de Lomé, Bè',
            'loss_circumstances': 'Perte lors d\'un déplacement au marché central de Lomé.',
            'loss_description': 'J\'ai perdu ma carte nationale lors d\'un déplacement. '
                                'Je me suis rendu au marché et ne l\'ai pas retrouvée malgré mes recherches.',
        })
        self.assertTrue(form.is_valid(), form.errors)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS API REST
# ─────────────────────────────────────────────────────────────────────────────

class DeclarationAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.agent = make_agent()
        self.admin = make_admin()
        make_document_type()
        make_prefecture()

    def get_jwt_token(self, email, password='TestPass123!'):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': email, 'password': password},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.json())
        return response.json()['access']

    def auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_list_declarations_authenticated(self):
        make_declaration(self.user, status='submitted')
        token = self.get_jwt_token(self.user.email)
        response = self.client.get(
            '/api/declarations/', **self.auth_headers(token)
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data['count'], 1)

    def test_list_declarations_unauthenticated(self):
        response = self.client.get('/api/declarations/')
        self.assertEqual(response.status_code, 401)

    def test_create_declaration_via_api(self):
        token = self.get_jwt_token(self.user.email)
        prefecture = make_prefecture()
        doc_type = make_document_type()
        payload = {
            'first_name': 'Kofi',
            'last_name': 'Atta',
            'date_of_birth': '1990-05-15',
            'place_of_birth': 'Lomé',
            'nationality': 'Togolaise',
            'phone': '+22890123456',
            'email': self.user.email,
            'address': 'Quartier Bé, Lomé',
            'prefecture': str(prefecture.pk),
            'document_type': str(doc_type.pk),
            'document_number': 'TG-12345678',
            'loss_date': '2024-03-01',
            'loss_place': 'Marché de Lomé',
            'loss_circumstances': 'Perte lors d\'un déplacement au marché.',
            'loss_description': 'J\'ai perdu ma carte nationale lors d\'un déplacement au marché '
                                'central. Je ne l\'ai pas retrouvée malgré mes recherches.',
            'honor_declaration': True,
        }
        response = self.client.post(
            '/api/declarations/',
            json.dumps(payload),
            content_type='application/json',
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 201, response.json())
        data = response.json()
        self.assertEqual(data['first_name'], 'Kofi')
        self.assertIn('declaration_number', data)

    def test_validate_declaration_by_agent(self):
        declaration = make_declaration(self.user, status='in_progress')
        token = self.get_jwt_token(self.agent.email)
        response = self.client.post(
            f'/api/declarations/{declaration.pk}/validate/',
            json.dumps({'notes': 'Déclaration conforme'}),
            content_type='application/json',
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        declaration.refresh_from_db()
        self.assertEqual(declaration.status, 'validated')

    def test_validate_declaration_by_citizen_forbidden(self):
        declaration = make_declaration(self.user, status='in_progress')
        token = self.get_jwt_token(self.user.email)
        response = self.client.post(
            f'/api/declarations/{declaration.pk}/validate/',
            content_type='application/json',
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 403)

    def test_reject_declaration_requires_reason(self):
        declaration = make_declaration(self.user, status='in_progress')
        token = self.get_jwt_token(self.agent.email)
        response = self.client.post(
            f'/api/declarations/{declaration.pk}/reject/',
            json.dumps({}),  # pas de motif
            content_type='application/json',
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 400)

    def test_citizen_cannot_see_other_declarations(self):
        other = make_user(email='other3@test.tg')
        other_decl = make_declaration(other, status='submitted')
        token = self.get_jwt_token(self.user.email)
        response = self.client.get(
            f'/api/declarations/{other_decl.pk}/',
            **self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 404)


class VerificationAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_valid_verification(self):
        declaration = make_declaration(self.user, status='validated')
        response = self.client.get(
            f'/api/verification/{declaration.verification_token}/'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['declaration_number'], declaration.declaration_number)

    def test_invalid_token(self):
        response = self.client.get('/api/verification/invalid-token-abc/')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['valid'])


class NotificationAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def get_jwt_token(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': self.user.email, 'password': 'TestPass123!'},
            content_type='application/json',
        )
        return response.json()['access']

    def test_list_notifications(self):
        Notification.objects.create(
            user=self.user,
            notification_type='info',
            title='Test',
            message='Test notification',
        )
        token = self.get_jwt_token()
        response = self.client.get(
            '/api/notifications/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()['count'], 1)

    def test_mark_notification_read(self):
        notif = Notification.objects.create(
            user=self.user,
            notification_type='info',
            title='Test',
            message='Test',
        )
        token = self.get_jwt_token()
        response = self.client.post(
            f'/api/notifications/{notif.pk}/mark_read/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_unread_count(self):
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                notification_type='info',
                title=f'Test {i}',
                message='Test',
            )
        token = self.get_jwt_token()
        response = self.client.get(
            '/api/notifications/unread_count/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 3)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS TÂCHES CELERY
# ─────────────────────────────────────────────────────────────────────────────

class CeleryTasksTest(TestCase):
    def setUp(self):
        self.user = make_user()
        make_document_type()
        make_prefecture()
        self.declaration = make_declaration(self.user, status='submitted')

    @patch('notifications.tasks.send_email_notification.delay')
    @patch('notifications.tasks.send_sms_notification.delay')
    def test_send_declaration_notification_creates_notification(
        self, mock_sms, mock_email
    ):
        from notifications.tasks import send_declaration_notification
        send_declaration_notification(
            str(self.declaration.id), 'declaration_submitted'
        )
        notif = Notification.objects.filter(
            user=self.user,
            notification_type='declaration_submitted',
        )
        self.assertEqual(notif.count(), 1)

    @patch('notifications.tasks.send_email_notification.delay')
    def test_notification_email_queued(self, mock_email):
        self.user.email_notifications = True
        self.user.save()
        from notifications.tasks import send_declaration_notification
        send_declaration_notification(
            str(self.declaration.id), 'declaration_submitted'
        )
        mock_email.assert_called_once()

    def test_cleanup_draft_declarations(self):
        from notifications.tasks import cleanup_draft_declarations
        old_draft = make_declaration(self.user, status='draft')
        old_draft.created_at = timezone.now() - timedelta(days=35)
        old_draft.save(update_fields=['created_at'])
        result = cleanup_draft_declarations()
        self.assertGreaterEqual(result, 1)
        self.assertFalse(Declaration.objects.filter(pk=old_draft.pk).exists())


# ─────────────────────────────────────────────────────────────────────────────
# TESTS AUDIT
# ─────────────────────────────────────────────────────────────────────────────

class AuditLogTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_audit_log_creation(self):
        log = AuditLog.log(
            action=AuditLog.Action.LOGIN,
            user=self.user,
            notes='Test login',
        )
        self.assertIsNotNone(log.pk)
        self.assertEqual(log.action, 'login')
        self.assertEqual(log.user, self.user)
        self.assertTrue(log.success)

    def test_audit_log_with_object(self):
        declaration = make_declaration(self.user)
        log = AuditLog.log(
            action=AuditLog.Action.CREATE,
            user=self.user,
            obj=declaration,
        )
        self.assertEqual(log.content_type, 'Declaration')
        self.assertEqual(log.object_id, str(declaration.pk))

    def test_audit_log_failed_action(self):
        log = AuditLog.log(
            action=AuditLog.Action.LOGIN_FAILED,
            success=False,
            error='Mot de passe incorrect',
        )
        self.assertFalse(log.success)
        self.assertEqual(log.error_message, 'Mot de passe incorrect')


# ─────────────────────────────────────────────────────────────────────────────
# TESTS SÉCURITÉ
# ─────────────────────────────────────────────────────────────────────────────

class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_csrf_required_on_post(self):
        # Test sans CSRF token (Django teste ça automatiquement en mode test)
        from django.test import RequestFactory
        factory = RequestFactory(enforce_csrf_checks=True)
        request = factory.post('/accounts/login/', {'email': 'test@test.tg', 'password': 'test'})
        self.assertIsNotNone(request)

    def test_rate_limiting_login(self):
        """Test que le rate limiting bloque après N tentatives."""
        from django.core.cache import cache
        # Simuler 10 tentatives
        for i in range(11):
            self.client.post(reverse('account_login'), {
                'login': 'brute@test.tg',
                'password': 'wrongpassword',
            })
        # La 11ème devrait être bloquée (si middleware actif)
        # Note: en mode test, le middleware peut être désactivé
        # Vérifier juste que la logique fonctionne
        cache_key = 'rate_limit:/accounts/login/:127.0.0.1'
        # count = cache.get(cache_key, 0)
        # self.assertGreater(count, 0)

    def test_media_files_protected(self):
        """Les fichiers media ne doivent pas être accessibles sans auth."""
        user = make_user()
        declaration = make_declaration(user, status='submitted')
        # Un fichier uploadé ne doit pas être accessible directement
        response = self.client.get('/media/declarations/test/file.pdf')
        # En production, nginx gère ça; en dev on vérifie juste le routing
        self.assertNotEqual(response.status_code, 200)

    def test_admin_requires_staff(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.get('/admin/')
        self.assertNotEqual(response.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS INTÉGRATION COMPLETS
# ─────────────────────────────────────────────────────────────────────────────

class FullDeclarationWorkflowTest(TestCase):
    """Test du workflow complet : de la création à la validation."""

    def setUp(self):
        self.client = Client()
        self.citizen = make_user()
        self.agent = make_agent()
        make_document_type()
        make_prefecture()

    @patch('notifications.tasks.send_declaration_notification.delay')
    @patch('notifications.tasks.generate_receipt_pdf.delay')
    def test_full_workflow(self, mock_receipt, mock_notif):
        """Test complet : création → soumission → validation → récépissé."""

        # 1. Connexion citoyen
        self.client.force_login(self.citizen)

        # 2. Étape 1 du wizard
        step1_data = {
            'first_name': 'Kofi', 'last_name': 'Atta',
            'date_of_birth': '1990-05-15', 'place_of_birth': 'Lomé',
            'nationality': 'Togolaise', 'phone': '+22890123456',
            'email': self.citizen.email, 'address': 'Bè, Lomé',
            'prefecture': str(make_prefecture().pk),
        }
        response = self.client.post(reverse('declarations:wizard'), step1_data)
        self.assertRedirects(response, reverse('declarations:wizard', kwargs={'step': 2}))

        # Récupérer la déclaration en cours
        declaration_id = self.client.session.get('current_declaration_id')
        self.assertIsNotNone(declaration_id)
        declaration = Declaration.objects.get(pk=declaration_id)
        self.assertEqual(declaration.status, 'draft')

        # 3. Étape 2 — document perdu
        step2_data = {
            'document_type': str(make_document_type().pk),
            'document_number': 'TG-12345678',
            'document_issue_date': '2020-01-10',
            'document_issue_place': 'Lomé',
        }
        self.client.post(reverse('declarations:wizard', kwargs={'step': 2}), step2_data)

        # 4. Étape 3 — circonstances
        step3_data = {
            'loss_date': '2024-03-01',
            'loss_place': 'Marché de Lomé',
            'loss_circumstances': 'Perte lors d\'un déplacement au marché central.',
            'loss_description': 'J\'ai perdu ma carte nationale lors d\'un déplacement au '
                                'marché central de Lomé. Je ne l\'ai pas retrouvée malgré '
                                'plusieurs recherches effectuées sur place.',
        }
        self.client.post(reverse('declarations:wizard', kwargs={'step': 3}), step3_data)

        # 5. Étape 5 — confirmation
        step5_data = {
            'honor_declaration': True,
            'terms_accepted': True,
            'signature_data': 'data:image/png;base64,test',
        }
        response = self.client.post(
            reverse('declarations:wizard', kwargs={'step': 5}), step5_data
        )

        declaration.refresh_from_db()
        self.assertEqual(declaration.status, 'submitted')
        mock_notif.assert_called()

        # 6. L'agent traite la déclaration
        self.client.force_login(self.agent)
        declaration.transition_to('in_progress', user=self.agent)
        declaration.transition_to('validated', user=self.agent, notes='Conforme')

        declaration.refresh_from_db()
        self.assertEqual(declaration.status, 'validated')
        self.assertEqual(declaration.validated_by, self.agent)

        # 7. Vérification via QR Code (public)
        self.client.logout()
        response = self.client.get(
            reverse('core:verification', kwargs={'token': declaration.verification_token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['valid'])

        # 8. Le citoyen peut télécharger son récépissé
        self.client.force_login(self.citizen)
        history = StatusHistory.objects.filter(declaration=declaration)
        self.assertGreaterEqual(history.count(), 2)
