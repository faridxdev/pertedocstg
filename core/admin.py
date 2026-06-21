"""
PerteDocsTG — Interface d'administration Django personnalisée
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, AgentProfile
from declarations.models import Declaration, DocumentType, StatusHistory
from documents.models import Attachment, Receipt
from notifications.models import Notification, EmailLog, SMSLog
from audit.models import AuditLog
from core.models import Region, Prefecture, Commune, SiteConfiguration


# ─── Comptes ─────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'get_full_name', 'role', 'is_active', 'is_verified',
                    'declarations_count', 'created_at']
    list_filter = ['role', 'is_active', 'is_verified', 'is_staff', 'dark_mode']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_login_ip']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender',
                       'nationality', 'phone', 'avatar')
        }),
        (_('Adresse'), {'fields': ('address', 'city', 'prefecture')}),
        (_('Rôle et permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser',
                       'is_verified', 'is_phone_verified', 'groups', 'user_permissions')
        }),
        (_('Sécurité'), {
            'fields': ('two_factor_enabled', 'failed_login_attempts',
                       'locked_until', 'last_login_ip')
        }),
        (_('Préférences'), {
            'fields': ('language', 'dark_mode', 'email_notifications', 'sms_notifications')
        }),
        (_('Dates'), {'fields': ('created_at', 'updated_at', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = _('Nom complet')

    def declarations_count(self, obj):
        count = obj.declarations.count()
        if count:
            url = reverse('admin:declarations_declaration_changelist') + f'?declarant__id={obj.pk}'
            return format_html('<a href="{}">{}</a>', url, count)
        return 0
    declarations_count.short_description = _('Déclarations')


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'agent_id', 'agent_type', 'department', 'prefecture', 'is_active']
    list_filter = ['agent_type', 'is_active', 'prefecture__region']
    search_fields = ['user__email', 'agent_id', 'department']


# ─── Déclarations ─────────────────────────────────────────────────────────────

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ['original_name', 'file_size', 'mime_type', 'checksum', 'created_at']
    fields = ['attachment_type', 'file', 'original_name', 'file_size', 'is_valid', 'created_at']


class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'changed_by', 'notes', 'created_at']
    can_delete = False


@admin.register(Declaration)
class DeclarationAdmin(admin.ModelAdmin):
    list_display = ['declaration_number', 'full_name', 'document_type', 'status_badge',
                    'prefecture', 'submitted_at', 'processed_at', 'assigned_agent']
    list_filter = ['status', 'document_type', 'prefecture__region', 'prefecture',
                   'receipt_generated']
    search_fields = ['declaration_number', 'full_name', 'phone', 'email',
                     'document_number', 'declarant__email']
    readonly_fields = ['declaration_number', 'verification_token', 'full_name',
                       'created_at', 'updated_at', 'submitted_at', 'processed_at',
                       'receipt_generated_at', 'ip_address']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    inlines = [AttachmentInline, StatusHistoryInline]

    fieldsets = (
        (_('Référence'), {
            'fields': ('declaration_number', 'verification_token', 'status',
                       'declarant', 'assigned_agent')
        }),
        (_('Déclarant'), {
            'fields': ('full_name', 'first_name', 'last_name', 'date_of_birth',
                       'place_of_birth', 'nationality', 'phone', 'email',
                       'profession', 'address', 'prefecture')
        }),
        (_('Document perdu'), {
            'fields': ('document_type', 'document_number', 'document_issue_date',
                       'document_issue_place', 'document_authority')
        }),
        (_('Circonstances'), {
            'fields': ('loss_date', 'loss_place', 'loss_circumstances', 'loss_description')
        }),
        (_('Traitement'), {
            'fields': ('agent_notes', 'rejection_reason', 'complement_requested',
                       'validated_by', 'processing_started_at', 'processed_at')
        }),
        (_('Récépissé'), {
            'fields': ('receipt_generated', 'receipt_file', 'receipt_generated_at',
                       'receipt_expires_at')
        }),
        (_('Signature'), {
            'fields': ('honor_declaration', 'signature_date', 'ip_address'),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_in_progress', 'export_csv']

    def status_badge(self, obj):
        colors = {
            'draft': '#6B7280',
            'submitted': '#3B82F6',
            'in_progress': '#F59E0B',
            'under_review': '#8B5CF6',
            'validated': '#10B981',
            'rejected': '#EF4444',
            'archived': '#9CA3AF',
            'complement_requested': '#F97316',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = _('Statut')

    def mark_in_progress(self, request, queryset):
        count = 0
        for decl in queryset.filter(status='submitted'):
            if decl.transition_to('in_progress', user=request.user):
                count += 1
        self.message_user(request, f'{count} déclarations passées en traitement.')
    mark_in_progress.short_description = _('Passer en cours de traitement')

    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="declarations.csv"'
        response.write('\ufeff')  # BOM pour Excel
        writer = csv.writer(response)
        writer.writerow(['Numéro', 'Nom', 'Téléphone', 'Email', 'Document',
                         'Statut', 'Date soumission', 'Date traitement'])
        for d in queryset:
            writer.writerow([
                d.declaration_number, d.full_name, d.phone, d.email,
                d.document_type.name, d.get_status_display(),
                d.submitted_at.strftime('%d/%m/%Y %H:%M') if d.submitted_at else '',
                d.processed_at.strftime('%d/%m/%Y %H:%M') if d.processed_at else '',
            ])
        return response
    export_csv.short_description = _('Exporter en CSV')


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'requires_number', 'processing_days',
                    'is_active', 'order']
    list_editable = ['is_active', 'order', 'processing_days']
    list_filter = ['is_active', 'requires_number']
    search_fields = ['name', 'code']


# ─── Documents ────────────────────────────────────────────────────────────────

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'declaration', 'attachment_type', 'file_size',
                    'mime_type', 'is_valid', 'is_virus_scanned', 'created_at']
    list_filter = ['attachment_type', 'is_valid', 'is_virus_scanned', 'mime_type']
    search_fields = ['original_name', 'declaration__declaration_number']
    readonly_fields = ['checksum', 'file_size', 'mime_type', 'created_at']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'declaration', 'is_valid', 'issued_at',
                    'expires_at', 'download_count']
    list_filter = ['expires_at']
    search_fields = ['receipt_number', 'declaration__declaration_number']
    readonly_fields = ['issued_at', 'download_count', 'digital_signature']


# ─── Notifications ────────────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'channel',
                    'is_read', 'sent', 'created_at']
    list_filter = ['notification_type', 'channel', 'is_read', 'sent']
    search_fields = ['title', 'user__email', 'message']
    readonly_fields = ['created_at', 'sent_at', 'read_at']
    date_hierarchy = 'created_at'


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient_email', 'sent', 'sent_at', 'created_at']
    list_filter = ['sent']
    search_fields = ['subject', 'recipient_email']
    readonly_fields = ['sent_at', 'created_at']


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_phone', 'sent', 'cost', 'sent_at', 'created_at']
    list_filter = ['sent']
    search_fields = ['recipient_phone', 'message']
    readonly_fields = ['sent_at', 'created_at', 'provider_response']


# ─── Audit ────────────────────────────────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'action', 'content_type',
                    'object_repr', 'ip_address', 'success']
    list_filter = ['action', 'success', 'created_at']
    search_fields = ['user__email', 'object_repr', 'ip_address', 'notes']
    readonly_fields = ['created_at', 'user', 'action', 'content_type', 'object_id',
                       'object_repr', 'changes', 'ip_address', 'user_agent',
                       'session_key', 'success', 'error_message', 'notes']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ─── Géographie ──────────────────────────────────────────────────────────────

class PrefectureInline(admin.TabularInline):
    model = Prefecture
    extra = 0
    fields = ['name', 'code', 'capital', 'is_active']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'capital', 'prefectures_count', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    inlines = [PrefectureInline]

    def prefectures_count(self, obj):
        return obj.prefectures.count()
    prefectures_count.short_description = _('Préfectures')


class CommuneInline(admin.TabularInline):
    model = Commune
    extra = 0
    fields = ['name', 'code', 'is_active']


@admin.register(Prefecture)
class PrefectureAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'region', 'capital', 'communes_count', 'is_active']
    list_filter = ['region', 'is_active']
    search_fields = ['name', 'code', 'capital']
    inlines = [CommuneInline]

    def communes_count(self, obj):
        return obj.communes.count()
    communes_count.short_description = _('Communes')


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'prefecture', 'is_active']
    list_filter = ['prefecture__region', 'is_active']
    search_fields = ['name', 'code']


# ─── Configuration ────────────────────────────────────────────────────────────

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Général'), {
            'fields': ('site_name', 'tagline', 'logo', 'favicon')
        }),
        (_('Contact'), {
            'fields': ('contact_email', 'contact_phone', 'address')
        }),
        (_('Configuration'), {
            'fields': ('allow_registrations', 'max_declarations_per_user',
                       'receipt_validity_days')
        }),
        (_('Maintenance'), {
            'fields': ('maintenance_mode', 'maintenance_message')
        }),
    )

    def has_add_permission(self, request):
        return not SiteConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
