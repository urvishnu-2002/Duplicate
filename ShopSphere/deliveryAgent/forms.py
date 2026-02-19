from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import DeliveryAgentProfile
from user.models import AuthUser

class AgentRegistrationForm(UserCreationForm):
    """Registration form for delivery agents"""
    # Personal Info
    phone_number = forms.CharField(max_length=15, required=True)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    
    # Address
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    city = forms.CharField(max_length=50, required=True)
    state = forms.CharField(max_length=50, required=True)
    postal_code = forms.CharField(max_length=10, required=True)
    
    # Vehicle
    vehicle_type = forms.ChoiceField(choices=DeliveryAgentProfile.VEHICLE_CHOICES, required=True)
    vehicle_number = forms.CharField(max_length=20, required=True)
    
    # Identity & License
    id_type = forms.ChoiceField(choices=[
        ('aadhar', 'Aadhar'),
        ('passport', 'Passport'),
        ('pan', 'PAN'),
        ('drivers_license', "Driver's License"),
    ], required=True)
    id_number = forms.CharField(max_length=50, required=True)
    id_proof_file = forms.FileField(required=True)
    
    license_number = forms.CharField(max_length=50, required=True)
    license_expires = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    license_file = forms.FileField(required=True)
    
    # Bank Details
    bank_holder_name = forms.CharField(max_length=100, required=True)
    bank_account_number = forms.CharField(max_length=20, required=True)
    bank_ifsc_code = forms.CharField(max_length=11, required=True)
    bank_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = AuthUser
        fields = ['username', 'email', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        style = 'w-full p-4 bg-gray-50 border-2 border-gray-100 rounded-xl font-medium focus:border-[#5D56D1] outline-none transition-all'
        
        for field_name, field in self.fields.items():
            current_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{current_class} {style}"
            field.widget.attrs['placeholder'] = field.label

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'delivery'
        user.phone = self.cleaned_data.get('phone_number')
        
        if commit:
            user.save()
            DeliveryAgentProfile.objects.create(
                user=user,
                phone_number=self.cleaned_data.get('phone_number'),
                date_of_birth=self.cleaned_data.get('date_of_birth'),
                
                address=self.cleaned_data.get('address'),
                city=self.cleaned_data.get('city'),
                state=self.cleaned_data.get('state'),
                postal_code=self.cleaned_data.get('postal_code'),
                
                vehicle_type=self.cleaned_data.get('vehicle_type'),
                vehicle_number=self.cleaned_data.get('vehicle_number'),
                
                id_type=self.cleaned_data.get('id_type'),
                id_number=self.cleaned_data.get('id_number'),
                id_proof_file=self.cleaned_data.get('id_proof_file'),
                
                license_number=self.cleaned_data.get('license_number'),
                license_expires=self.cleaned_data.get('license_expires'),
                license_file=self.cleaned_data.get('license_file'),
                
                bank_holder_name=self.cleaned_data.get('bank_holder_name'),
                bank_account_number=self.cleaned_data.get('bank_account_number'),
                bank_ifsc_code=self.cleaned_data.get('bank_ifsc_code'),
                bank_name=self.cleaned_data.get('bank_name'),
            )
        return user
