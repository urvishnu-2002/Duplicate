from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['name', 'phone', 'email', 'address_line1', 'address_line2', 'city', 'state', 'pincode', 'country', 'is_default']

'''class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['Product', 'user', 'rating', 'comment', 'pictures', 'created_at', 'updated_at']
        widgets = {
            'Product': forms.HiddenInput(),
            'user': forms.HiddenInput(),
            'rating': forms.NumberInput(attrs={'min':1, 'max':5}),
            'comment': forms.Textarea(attrs={'rows':50}),
            'pictures': forms.ClearableFileInput(attrs={'multiple': True}),
            'created_at': forms.HiddenInput(),
            'updated_at': forms.HiddenInput(),
        }
'''