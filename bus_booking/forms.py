from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Trip, Bus

class CustomUserCreationForm(UserCreationForm):
     
    username = forms.CharField(
        label='',
        help_text='',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    email = forms.EmailField(
        label='',
        help_text='',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'})
    )
    password1 = forms.CharField(
        label='',
        help_text='',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )
    password2 = forms.CharField(
        label='',
        help_text='',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    role = forms.CharField(
        widget=forms.HiddenInput(),
        initial=User.Roles.CUSTOMER
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['bus', 'origin', 'destination', 'departure_time', 'price']
        widgets = {
            'bus': forms.Select(attrs={'class': 'form-control'}),
            'origin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter origin'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter destination'}),
            'departure_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
        }

class BusUpdateForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = ['bus', 'origin', 'destination', 'departure_time', 'price']
        widgets = {
            'bus': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter bus name'}),
            'origin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter origin'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter destination'}),
            'departure_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
        }
