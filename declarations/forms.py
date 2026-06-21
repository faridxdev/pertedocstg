"""
PerteDocsTG - Formulaires de Déclaration Multi-étapes
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, HTML, Div, Row, Column
from .models import Declaration, DocumentType


class DeclarationStep1Form(forms.ModelForm):
    """Étape 1 : Informations personnelles du déclarant."""

    class Meta:
        model = Declaration
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'place_of_birth',
            'nationality', 'phone', 'email', 'profession', 'address', 'prefecture',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'max': timezone.now().date().isoformat()}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'first_name': _('Prénom'),
            'last_name': _('Nom de famille'),
            'date_of_birth': _('Date de naissance'),
            'place_of_birth': _('Lieu de naissance'),
            'nationality': _('Nationalité'),
            'phone': _('Numéro de téléphone'),
            'email': _('Adresse email'),
            'profession': _('Profession'),
            'address': _('Adresse complète'),
            'prefecture': _('Préfecture de résidence'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import Prefecture
        self.fields['prefecture'].queryset = Prefecture.objects.filter(
            is_active=True
        ).select_related('region').order_by('region__order', 'region__name', 'name')
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(Field('first_name', css_class='form-input'), css_class='col-span-6'),
                Column(Field('last_name', css_class='form-input'), css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4',
            ),
            Row(
                Column(Field('date_of_birth', css_class='form-input'), css_class='col-span-6'),
                Column(Field('place_of_birth', css_class='form-input'), css_class='col-span-6'),
                css_class='grid grid-cols-12 gap-4',
            ),
            Row(
                Column(Field('nationality', css_class='form-input'), css_class='col-span-4'),
                Column(Field('phone', css_class='form-input'), css_class='col-span-4'),
                Column(Field('email', css_class='form-input'), css_class='col-span-4'),
                css_class='grid grid-cols-12 gap-4',
            ),
            Field('profession', css_class='form-input'),
            Field('address', css_class='form-textarea'),
            Field('prefecture', css_class='form-select'),
        )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        # Format togolais: +228 XX XX XX XX ou 9X/7X/2X XXXXXX
        import re
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
        if not re.match(r'^(\+228|228)?[279]\d{7}$', phone_clean):
            raise forms.ValidationError(_('Numéro de téléphone invalide. Format attendu : +228 XX XX XX XX'))
        return phone

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > timezone.now().date():
            raise forms.ValidationError(_('La date de naissance ne peut pas être dans le futur.'))
        if dob:
            age = (timezone.now().date() - dob).days // 365
            if age < 15:
                raise forms.ValidationError(_('Vous devez avoir au moins 15 ans pour effectuer une déclaration.'))
        return dob


class DeclarationStep2Form(forms.ModelForm):
    """Étape 2 : Informations sur le document perdu."""

    class Meta:
        model = Declaration
        fields = [
            'document_type', 'document_number', 'document_issue_date',
            'document_issue_place', 'document_authority',
        ]
        widgets = {
            'document_issue_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'document_type': _('Type de document perdu'),
            'document_number': _('Numéro du document'),
            'document_issue_date': _('Date de délivrance'),
            'document_issue_place': _('Lieu de délivrance'),
            'document_authority': _('Autorité émettrice'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['document_type'].queryset = DocumentType.objects.filter(is_active=True)
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_document_issue_date(self):
        date = self.cleaned_data.get('document_issue_date')
        if date and date > timezone.now().date():
            raise forms.ValidationError(_('La date de délivrance ne peut pas être dans le futur.'))
        return date


class DeclarationStep3Form(forms.ModelForm):
    """Étape 3 : Circonstances de la perte."""

    class Meta:
        model = Declaration
        fields = ['loss_date', 'loss_place', 'loss_circumstances', 'loss_description']
        widgets = {
            'loss_date': forms.DateInput(attrs={'type': 'date'}),
            'loss_circumstances': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'loss_date': _('Date estimée de perte'),
            'loss_place': _('Lieu de perte'),
            'loss_circumstances': _('Circonstances de la perte'),
            'loss_description': _('Description détaillée'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['loss_description'].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_loss_date(self):
        date = self.cleaned_data.get('loss_date')
        if date and date > timezone.now().date():
            raise forms.ValidationError(_('La date de perte ne peut pas être dans le futur.'))
        return date


class DeclarationStep4Form(forms.Form):
    """Étape 4 : Pièces jointes."""

    attachment_1 = forms.FileField(
        label=_('Pièce jointe 1 (obligatoire)'),
        help_text=_('Justificatif d\'identité (PDF, JPG, PNG - max 20 Mo)'),
        widget=forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )
    attachment_2 = forms.FileField(
        label=_('Pièce jointe 2 (optionnelle)'),
        help_text=_('Document complémentaire'),
        required=False,
        widget=forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )
    attachment_3 = forms.FileField(
        label=_('Pièce jointe 3 (optionnelle)'),
        required=False,
        widget=forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
    )

    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 Mo
    ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ['attachment_1', 'attachment_2', 'attachment_3']:
            file = cleaned_data.get(field_name)
            if file:
                if file.size > self.MAX_FILE_SIZE:
                    self.add_error(field_name, _('Fichier trop volumineux. Taille maximale : 20 Mo.'))
                import os
                ext = os.path.splitext(file.name)[1].lower()
                if ext not in self.ALLOWED_EXTENSIONS:
                    self.add_error(field_name, _('Format de fichier non autorisé. Formats acceptés : PDF, JPG, PNG.'))
        return cleaned_data


class DeclarationStep5Form(forms.Form):
    """Étape 5 : Déclaration sur l'honneur et signature."""

    declaration_id = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput(),
    )
    honor_declaration = forms.BooleanField(
        label=_('Je soussigné(e) déclare sur l\'honneur que les informations fournies sont exactes et sincères, '
                'et que la perte du document susmentionné est réelle. Je reconnais être passible de poursuites '
                'judiciaires en cas de fausse déclaration.'),
        required=True,
        error_messages={'required': _('Vous devez accepter la déclaration sur l\'honneur.')},
    )
    terms_accepted = forms.BooleanField(
        label=_('J\'accepte les conditions d\'utilisation de la plateforme PerteDocsTG.'),
        required=True,
        error_messages={'required': _('Vous devez accepter les conditions d\'utilisation.')},
    )
    signature_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        label=_('Signature électronique'),
    )


class DeclarationSearchForm(forms.Form):
    """Formulaire de recherche des déclarations."""

    query = forms.CharField(
        label=_('Recherche'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Nom, téléphone, numéro de déclaration...')}),
    )
    status = forms.ChoiceField(
        label=_('Statut'),
        required=False,
        choices=[('', _('Tous les statuts'))] + Declaration.Status.choices,
    )
    document_type = forms.ModelChoiceField(
        label=_('Type de document'),
        queryset=DocumentType.objects.filter(is_active=True),
        required=False,
        empty_label=_('Tous les types'),
    )
    date_from = forms.DateField(
        label=_('Du'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    date_to = forms.DateField(
        label=_('Au'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    prefecture = forms.ModelChoiceField(
        label=_('Préfecture'),
        queryset=None,
        required=False,
        empty_label=_('Toutes les préfectures'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import Prefecture
        self.fields['prefecture'].queryset = Prefecture.objects.filter(is_active=True)
