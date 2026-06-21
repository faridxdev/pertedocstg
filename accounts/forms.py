from django import forms
from django.utils.translation import gettext_lazy as _

class SignupForm(forms.Form):
    """Formulaire d'inscription enrichi pour django-allauth."""
    first_name = forms.CharField(
        label=_('Prénom'),
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Ex: Kofi', 'autocomplete': 'given-name'}),
    )
    last_name = forms.CharField(
        label=_('Nom de famille'),
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Ex: Atta', 'autocomplete': 'family-name'}),
    )
    phone = forms.CharField(
        label=_('Téléphone'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+228 90 12 34 56'}),
    )
    terms = forms.BooleanField(
        label=_("J'accepte les conditions d'utilisation"),
        required=True,
        error_messages={'required': _("Vous devez accepter les conditions d'utilisation.")},
    )

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if self.cleaned_data.get('phone'):
            user.phone = self.cleaned_data['phone']
        user.save()

class UserForm(forms.ModelForm):
    pass