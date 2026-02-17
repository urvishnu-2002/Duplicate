from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import DeliveryAgentProfile
from user.models import AuthUser

class AgentRegistrationForm(UserCreationForm):
    """Registration form for delivery agents"""
    phone_number = forms.CharField(max_length=15, required=True)
    license_number = forms.CharField(max_length=50, required=True)
    vehicle_type = forms.ChoiceField(
        choices=DeliveryAgentProfile.VEHICLE_CHOICES,
        required=True
    )
    city = forms.CharField(max_length=50, required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)

    class Meta:
        model = AuthUser
        fields = ['username', 'email', 'password1', 'password2', 'phone_number', 'license_number', 'vehicle_type', 'city', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full p-5 bg-gray-50 border-2 border-gray-100 rounded-[2rem] font-bold tracking-wide focus:border-[#5D56D1] outline-none transition-all'
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'delivery_agent'
        user.phone = self.cleaned_data.get('phone_number')
        
        if commit:
            user.save()
        return user
