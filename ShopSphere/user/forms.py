from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['name', 'phone', 'email', 'address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'is_default']