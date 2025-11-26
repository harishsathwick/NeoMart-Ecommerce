from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Address, Product, Review


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'full_name', 'address_line', 'flat_house_no',
            'landmark', 'phone', 'email', 'pincode'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'address_line': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
            'flat_house_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat / House No'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nearby Landmark (Optional)'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
        }

        
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder':'Write your review...'}),
        }