from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, VendorProfile, CourierProfile

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password2', None)  # Remove password2 field
        self.fields['password1'].help_text = None

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password' in self.fields:
            self.fields['password'].help_text = "Raw passwords are not stored, so there is no way to see this user's password."

class AdminPasswordChangeForm(forms.Form):
    """A form used to change the password of a user in the admin interface."""
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text="Enter the new password.",
    )
    password2 = forms.CharField(
        label="Password (again)",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text="Enter the same password as before, for verification.",
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return password2

    def save(self, commit=True):
        """Save the new password."""
        password = self.cleaned_data["password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user

    @property
    def changed_data(self):
        data = super().changed_data
        for name in self.fields:
            if name not in data:
                return []
        return data

class VendorSignupForm(forms.Form):
    """Form for vendor signup"""
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    phone = forms.CharField(max_length=16, required=True)
    business_name = forms.CharField(max_length=255, required=True)
    business_address = forms.CharField(max_length=255, required=True)
    business_description = forms.CharField(widget=forms.Textarea, required=False)

class CourierSignupForm(forms.Form):
    """Form for courier signup"""
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    phone = forms.CharField(max_length=16, required=True)
    service_areas = forms.CharField(max_length=255, required=True)
    vehicle_type = forms.ChoiceField(choices=[
        ('bike', 'Bike'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('other', 'Other'),
    ], required=True)
    has_bike = forms.BooleanField(required=False)
