from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Enquiry


# ----------------------------
# ✅ Sign Up Form
# ----------------------------
class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


# ----------------------------
# ✅ Login Form
# ----------------------------
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-input'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-input'})
    )


# ----------------------------
# ✅ Enquiry/Contact Form
# ----------------------------
class EnquiryForm(forms.ModelForm):
    """Form for submitting enquiries/contact requests"""
    
    class Meta:
        model = Enquiry
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 000-0000 (Optional)',
                'required': False
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief subject of your enquiry',
                'required': True
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Please provide detailed information about your enquiry...',
                'rows': 6,
                'required': True
            }),
        }
        labels = {
            'name': '👤 Full Name',
            'email': '📧 Email Address',
            'phone': '📞 Phone Number',
            'subject': '📝 Subject',
            'message': '💬 Message',
        }
        help_texts = {
            'phone': 'Optional - We\'ll call you back if needed',
            'message': 'Please be as detailed as possible to help us assist you better',
        }

    def clean_email(self):
        """Normalize email address"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if '@' not in email:
                raise forms.ValidationError('Please enter a valid email address.')
        return email

    def clean_name(self):
        """Clean and validate name"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 2:
                raise forms.ValidationError('Name must be at least 2 characters long')
        return name

    def clean_message(self):
        """Validate message length"""
        message = self.cleaned_data.get('message')
        if message:
            message = message.strip()
            if len(message) < 10:
                raise forms.ValidationError('Please provide a more detailed message (at least 10 characters)')
            if len(message) > 5000:
                raise forms.ValidationError('Message is too long (maximum 5000 characters)')
        return message

    def clean_phone(self):
        """Clean phone number"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove common separators
            phone = phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        return phone if phone else ''