"""
PerteDocsTG - Tâches Celery pour les Notifications (corrigé)
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


def _safe_delay(task_func, *args, **kwargs):
    """Lance une tâche Celery, retombe en synchrone si le broker est indisponible."""
    try:
        from kombu.exceptions import OperationalError as KombuError
        task_func.delay(*args, **kwargs)
    except Exception as exc:
        logger.warning('Broker indisponible, exécution synchrone : %s', exc)
        task_func(*args, **kwargs)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_declaration_notification(self, declaration_id: str, notification_type: str):
    """Envoie les notifications pour une déclaration."""
    try:
        send_declaration_notification_sync(declaration_id, notification_type)
    except Exception as exc:
        logger.error('Notification échouée %s/%s: %s', declaration_id, notification_type, exc)
        raise self.retry(exc=exc)


def send_declaration_notification_sync(declaration_id: str, notification_type: str):
    """Envoie les notifications pour une déclaration (sans Celery)."""
    from declarations.models import Declaration
    from .models import Notification

    try:
        declaration = Declaration.objects.select_related('declarant', 'document_type').get(
            id=declaration_id
        )
    except Declaration.DoesNotExist:
        logger.error('Déclaration %s introuvable', declaration_id)
        return

    user = declaration.declarant
    doc_name = declaration.document_type.name if declaration.document_type else 'document'
    configs = {
        'declaration_submitted': {
            'title': f'Déclaration {declaration.declaration_number} reçue ✓',
            'message': (
                f'Votre déclaration de perte de {doc_name} '
                f'(n° {declaration.declaration_number}) a bien été reçue. '
                f'Un agent va traiter votre dossier sous 48–72h ouvrables.'
            ),
            'subject': f'[PerteDocsTG] Déclaration {declaration.declaration_number} — Reçue',
            'template': 'emails/declaration_submitted.html',
        },
        'declaration_validated': {
            'title': f'Déclaration {declaration.declaration_number} validée ✓',
            'message': (
                f'Bonne nouvelle ! Votre déclaration n° {declaration.declaration_number} '
                f'a été validée. Téléchargez votre récépissé officiel.'
            ),
            'subject': f'[PerteDocsTG] Déclaration {declaration.declaration_number} — Validée',
            'template': 'emails/declaration_validated.html',
        },
        'declaration_rejected': {
            'title': f'Déclaration {declaration.declaration_number} rejetée',
            'message': (
                f'Votre déclaration n° {declaration.declaration_number} a été rejetée. '
                f'Motif : {declaration.rejection_reason or "voir détails"}'
            ),
            'subject': f'[PerteDocsTG] Déclaration {declaration.declaration_number} — Rejetée',
            'template': 'emails/declaration_submitted.html',
        },
        'complement_requested': {
            'title': f'Complément requis — {declaration.declaration_number}',
            'message': (
                f'Un complément est requis pour votre déclaration '
                f'n° {declaration.declaration_number}. Connectez-vous pour voir les détails.'
            ),
            'subject': f'[PerteDocsTG] Complément requis — {declaration.declaration_number}',
            'template': 'emails/declaration_submitted.html',
        },
        'receipt_ready': {
            'title': f'Récépissé disponible — {declaration.declaration_number}',
            'message': 'Votre récépissé officiel est prêt à être téléchargé.',
            'subject': '[PerteDocsTG] Récépissé disponible',
            'template': 'emails/declaration_validated.html',
        },
        'document_found': {
            'title': '🎉 Votre document a été retrouvé !',
            'message': (
                f'Un de vos documents déclarés perdus (n° {declaration.declaration_number}) '
                f'a été retrouvé. Rendez-vous au bureau indiqué pour le récupérer.'
            ),
            'subject': f'[PerteDocsTG] Document retrouvé — {declaration.declaration_number}',
            'template': 'emails/document_found.html',
        },
    }

    config = configs.get(notification_type)
    if not config:
        logger.warning('Type de notification inconnu : %s', notification_type)
        return

    Notification.objects.create(
        user=user,
        declaration=declaration,
        notification_type=notification_type,
        channel=Notification.Channel.INTERNAL,
        title=config['title'],
        message=config['message'],
    )

    if getattr(user, 'email_notifications', True) and user.email:
        try:
            send_email_notification.delay(
                user_email=user.email,
                user_name=user.get_full_name(),
                declaration_number=declaration.declaration_number,
                subject=config['subject'],
                template=config['template'],
                declaration_id=str(declaration.id),
            )
        except Exception as exc:
            logger.warning('Email en synchrone: %s', exc)
            send_email_notification_sync(
                user_email=user.email,
                user_name=user.get_full_name(),
                declaration_number=declaration.declaration_number,
                subject=config['subject'],
                template=config['template'],
                declaration_id=str(declaration.id),
            )

    logger.info('Notification %s envoyée pour %s', notification_type, declaration.declaration_number)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_email_notification(self, user_email: str, user_name: str,
                             declaration_number: str, subject: str,
                             template: str, declaration_id: str = None):
    """Envoie un email de notification — version robuste sans template _txt."""
    try:
        send_email_notification_sync(
            user_email, user_name, declaration_number, subject, template, declaration_id
        )
    except Exception as exc:
        raise self.retry(exc=exc)


def send_email_notification_sync(user_email: str, user_name: str,
                                  declaration_number: str, subject: str,
                                  template: str, declaration_id: str = None):
    """Envoie un email de notification (sans Celery)."""
    from .models import EmailLog
    from declarations.models import Declaration

    declaration = None
    if declaration_id:
        try:
            declaration = Declaration.objects.select_related(
                'document_type', 'declarant'
            ).get(id=declaration_id)
        except Declaration.DoesNotExist:
            pass

    context = {
        'user_name': user_name,
        'declaration': declaration,
        'declaration_number': declaration_number,
        'site_name': 'PerteDocsTG',
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@pertedocs.tg'),
    }

    try:
        html_content = render_to_string(template, context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )
        email.attach_alternative(html_content, 'text/html')
        email.send()

        EmailLog.objects.create(
            recipient_email=user_email,
            subject=subject,
            body_html=html_content,
            sent=True,
            sent_at=timezone.now(),
        )
        logger.info('Email envoyé à %s', user_email)

    except Exception as exc:
        EmailLog.objects.create(
            recipient_email=user_email,
            subject=subject,
            sent=False,
            error=str(exc),
        )
        logger.error('Erreur email à %s: %s', user_email, exc)
        raise


@shared_task
def notify_document_found(declaration_id: str, found_record_id: str):
    """Notifie le citoyen que son document a été retrouvé."""
    from declarations.models import Declaration, DocumentFound
    try:
        declaration = Declaration.objects.select_related('declarant').get(id=declaration_id)
        found = DocumentFound.objects.get(id=found_record_id)
        found.notified_at = timezone.now()
        found.status = DocumentFound.FoundStatus.NOTIFIED
        found.save(update_fields=['notified_at', 'status'])

        # Notifier avec fallback synchrone si le broker Celery est indisponible
        try:
            send_declaration_notification.delay(declaration_id, 'document_found')
        except Exception as broker_exc:
            logger.warning('Broker indisponible, exécution synchrone: %s', broker_exc)
            send_declaration_notification_sync(declaration_id, 'document_found')

        logger.info(f'Notification document retrouvé envoyée pour {declaration.declaration_number}')
    except Exception as exc:
        logger.error(f'Erreur notify_document_found: {exc}')
        raise


def generate_receipt_for_declaration(declaration_id: str):
    """Génère le récépissé PDF (appel synchrone, utilisable hors Celery)."""
    from declarations.models import Declaration
    from documents.services import ReceiptService

    declaration = Declaration.objects.select_related(
        'document_type', 'declarant', 'validated_by'
    ).get(id=declaration_id, status='validated')
    ReceiptService.generate_receipt(declaration)
    try:
        send_declaration_notification.delay(declaration_id, 'receipt_ready')
    except Exception as exc:
        logger.warning('Notification récépissé en synchrone: %s', exc)
        send_declaration_notification_sync(declaration_id, 'receipt_ready')
    logger.info('Récépissé généré pour %s', declaration.declaration_number)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_receipt_pdf(self, declaration_id: str):
    """Génère le récépissé PDF avec QR code pour une déclaration validée."""
    from declarations.models import Declaration
    try:
        generate_receipt_for_declaration(declaration_id)
    except Declaration.DoesNotExist:
        logger.error('Déclaration %s introuvable ou non validée pour récépissé', declaration_id)
    except Exception as exc:
        logger.error('Erreur génération récépissé %s: %s', declaration_id, exc)
        raise self.retry(exc=exc)


@shared_task
def cleanup_draft_declarations():
    """Nettoie les déclarations brouillon de plus de 30 jours."""
    from declarations.models import Declaration
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = Declaration.objects.filter(
        status='draft', created_at__lt=cutoff
    ).delete()
    logger.info(f'{deleted_count} brouillons supprimés')
    return deleted_count
