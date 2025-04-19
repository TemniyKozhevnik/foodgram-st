from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
    AuthenticationForm
)
from .models import Client


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email', max_length=254)

    def clean_username(self):
        email = self.cleaned_data.get('username')
        if not Client.objects.filter(email=email).exists():
            raise forms.ValidationError("Email не зарегистрирован.")
        return email
    

class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = Client
        fields = ('email', )


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = Client
        fields = ('email', )