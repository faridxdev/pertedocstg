"""
PerteDocsTG - API REST (DRF) - Serializers et Vues
"""

from rest_framework import serializers, viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _

from declarations.models import Declaration, DocumentType, StatusHistory
from accounts.models import User
from documents.models import Attachment, Receipt
from notifications.models import Notification


# ─────────────────────────────────────────────────────────────────────────────
# SERIALIZERS
# ─────────────────────────────────────────────────────────────────────────────

class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ['id', 'code', 'name', 'description', 'requires_number',
                  'processing_days', 'is_active']


class UserPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'role']


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserPublicSerializer(read_only=True)
    old_status_label = serializers.CharField(source='get_old_status_display', read_only=True)
    new_status_label = serializers.CharField(source='get_new_status_display', read_only=True)

    class Meta:
        model = StatusHistory
        fields = ['id', 'old_status', 'old_status_label', 'new_status', 'new_status_label',
                  'changed_by', 'notes', 'created_at']


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'attachment_type', 'original_name', 'file_size', 'mime_type',
                  'is_valid', 'file_url', 'created_at']

    def get_file_url(self, obj) -> str:
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return ''


class DeclarationListSerializer(serializers.ModelSerializer):
    """Sérialiseur allégé pour les listes."""

    document_type_name = serializers.CharField(source='document_type.name', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    declarant_name = serializers.CharField(source='declarant.get_full_name', read_only=True)

    class Meta:
        model = Declaration
        fields = [
            'id', 'declaration_number', 'status', 'status_label',
            'document_type_name', 'full_name', 'declarant_name',
            'loss_date', 'submitted_at', 'created_at',
        ]


class DeclarationDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur complet pour le détail."""

    document_type = DocumentTypeSerializer(read_only=True)
    declarant = UserPublicSerializer(read_only=True)
    assigned_agent = UserPublicSerializer(read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = Declaration
        fields = [
            'id', 'declaration_number', 'verification_token', 'verification_url',
            'status', 'status_label', 'declarant', 'assigned_agent',
            # Déclarant
            'full_name', 'first_name', 'last_name', 'date_of_birth', 'place_of_birth',
            'nationality', 'phone', 'email', 'profession', 'address',
            # Document
            'document_type', 'document_number', 'document_issue_date',
            'document_issue_place', 'document_authority',
            # Perte
            'loss_date', 'loss_place', 'loss_circumstances', 'loss_description',
            # Admin
            'agent_notes', 'rejection_reason', 'complement_requested',
            # Récépissé
            'receipt_generated', 'receipt_generated_at', 'receipt_expires_at',
            # Relations
            'status_history', 'attachments',
            # Timestamps
            'created_at', 'updated_at', 'submitted_at', 'processed_at',
        ]
        read_only_fields = [
            'id', 'declaration_number', 'verification_token', 'declarant',
            'status_history', 'attachments', 'receipt_generated',
        ]

    def get_verification_url(self, obj) -> str:
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.get_verification_url())
        return ''


class DeclarationCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la création de déclaration via API."""

    class Meta:
        model = Declaration
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'place_of_birth',
            'nationality', 'phone', 'email', 'profession', 'address', 'prefecture',
            'document_type', 'document_number', 'document_issue_date',
            'document_issue_place', 'document_authority',
            'loss_date', 'loss_place', 'loss_circumstances', 'loss_description',
            'honor_declaration',
        ]

    def validate(self, attrs):
        if not attrs.get('honor_declaration'):
            raise serializers.ValidationError({
                'honor_declaration': _('La déclaration sur l\'honneur est obligatoire.')
            })
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['declarant'] = user
        validated_data['full_name'] = f"{validated_data['first_name']} {validated_data['last_name']}"
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read',
                  'read_at', 'created_at', 'icon', 'color']


class VerificationSerializer(serializers.Serializer):
    """Sérialiseur pour la vérification publique."""

    token = serializers.CharField(max_length=100)

    def validate_token(self, value: str):
        try:
            declaration = Declaration.objects.select_related('document_type').get(
                verification_token=value
            )
            self.declaration = declaration
        except Declaration.DoesNotExist:
            raise serializers.ValidationError(_('Token de vérification invalide.'))
        return value


# ─────────────────────────────────────────────────────────────────────────────
# PERMISSIONS
# ─────────────────────────────────────────────────────────────────────────────

class IsOwnerOrAgent(permissions.BasePermission):
    """Permission : propriétaire ou agent/admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_agent or request.user.is_administrator:
            return True
        if hasattr(obj, 'declarant'):
            return obj.declarant == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user


class IsAgentOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_agent or request.user.is_administrator
        )


# ─────────────────────────────────────────────────────────────────────────────
# VIEWSETS
# ─────────────────────────────────────────────────────────────────────────────

class DocumentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API des types de documents."""

    queryset = DocumentType.objects.filter(is_active=True)
    serializer_class = DocumentTypeSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']


class DeclarationViewSet(viewsets.ModelViewSet):
    """API CRUD des déclarations."""

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAgent]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'document_type', 'prefecture']
    search_fields = ['declaration_number', 'full_name', 'phone', 'email', 'document_number']
    ordering_fields = ['created_at', 'updated_at', 'submitted_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Declaration.objects.select_related(
            'document_type', 'declarant', 'assigned_agent', 'prefecture'
        ).prefetch_related('attachments', 'status_history')

        if user.is_agent or user.is_administrator:
            return qs
        return qs.filter(declarant=user)

    def get_serializer_class(self):
        if self.action == 'list':
            return DeclarationListSerializer
        if self.action == 'create':
            return DeclarationCreateSerializer
        return DeclarationDetailSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAgentOrAdmin])
    def validate(self, request, pk=None):
        """Valide une déclaration."""
        declaration = self.get_object()
        notes = request.data.get('notes', '')
        if declaration.transition_to('validated', user=request.user, notes=notes):
            from notifications.tasks import send_declaration_notification, generate_receipt_pdf
            send_declaration_notification.delay(str(declaration.id), 'declaration_validated')
            generate_receipt_pdf.delay(str(declaration.id))
            return Response({'status': 'validated', 'message': 'Déclaration validée avec succès.'})
        return Response(
            {'error': 'Transition non permise depuis le statut actuel.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAgentOrAdmin])
    def reject(self, request, pk=None):
        """Rejette une déclaration."""
        declaration = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'Le motif de rejet est obligatoire.'}, status=400)
        if declaration.transition_to('rejected', user=request.user, notes=reason):
            from notifications.tasks import send_declaration_notification
            send_declaration_notification.delay(str(declaration.id), 'declaration_rejected')
            return Response({'status': 'rejected', 'message': 'Déclaration rejetée.'})
        return Response({'error': 'Transition non permise.'}, status=400)

    @action(detail=True, methods=['post'], permission_classes=[IsAgentOrAdmin])
    def request_complement(self, request, pk=None):
        """Demande un complément d'informations."""
        declaration = self.get_object()
        complement = request.data.get('complement', '')
        if not complement:
            return Response({'error': 'Précisez le complément demandé.'}, status=400)
        if declaration.transition_to('complement_requested', user=request.user, notes=complement):
            from notifications.tasks import send_declaration_notification
            send_declaration_notification.delay(str(declaration.id), 'complement_requested')
            return Response({'status': 'complement_requested'})
        return Response({'error': 'Transition non permise.'}, status=400)

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        """Télécharge le récépissé PDF."""
        declaration = self.get_object()
        if not declaration.is_validated:
            return Response({'error': 'Récépissé non disponible.'}, status=400)
        try:
            from django.http import FileResponse
            receipt = declaration.receipt
            if not receipt.file:
                from documents.services import ReceiptService
                ReceiptService.generate_receipt(declaration)
                receipt.refresh_from_db()
            return FileResponse(receipt.file, as_attachment=True,
                                filename=f'recepisse-{declaration.declaration_number}.pdf')
        except Exception:
            return Response({'error': 'Récépissé non disponible.'}, status=404)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API des notifications utilisateur."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response({'marked_read': count})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'count': count})


class VerificationViewSet(viewsets.ViewSet):
    """API de vérification publique des récépissés."""

    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, pk=None):
        """Vérifie un token de récépissé."""
        try:
            declaration = Declaration.objects.select_related(
                'document_type', 'declarant'
            ).get(verification_token=pk)
            return Response({
                'valid': True,
                'declaration_number': declaration.declaration_number,
                'document_type': declaration.document_type.name,
                'declarant_name': declaration.full_name,
                'status': declaration.status,
                'status_label': declaration.get_status_display(),
                'is_validated': declaration.is_validated,
                'validated_at': declaration.processed_at,
                'loss_date': declaration.loss_date,
            })
        except Declaration.DoesNotExist:
            return Response({'valid': False, 'error': 'Token invalide.'}, status=404)


class StatisticsViewSet(viewsets.ViewSet):
    """API des statistiques (admin seulement)."""

    permission_classes = [permissions.IsAuthenticated, IsAgentOrAdmin]

    def list(self, request):
        """Statistiques globales."""
        from django.db.models import Count
        from declarations.models import Declaration

        data = {
            'total_declarations': Declaration.objects.count(),
            'by_status': list(Declaration.objects.values('status').annotate(count=Count('id'))),
            'by_document_type': list(
                Declaration.objects.values('document_type__name')
                .annotate(count=Count('id')).order_by('-count')[:10]
            ),
            'by_region': list(
                Declaration.objects.filter(prefecture__isnull=False)
                .values('prefecture__region__name')
                .annotate(count=Count('id')).order_by('-count')
            ),
            'total_users': User.objects.filter(role='citizen').count(),
        }
        return Response(data)
