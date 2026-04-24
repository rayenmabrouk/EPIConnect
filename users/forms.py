from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, StudentProfile

TAILWIND_INPUT = (
    'w-full px-4 py-2 border border-stone-300 rounded-lg '
    'focus:ring-2 focus:ring-primary-500 focus:border-primary-500 '
    'dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100 '
    'dark:placeholder-slate-500 bg-stone-50 text-gray-900'
)


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = TAILWIND_INPUT


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    student_id = forms.CharField(
        max_length=50,
        required=True,
        label='Student ID',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. EPI2024001'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'student_id', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = 'At least 6 characters.'
        self.fields['password2'].help_text = ''
        for field in self.fields.values():
            field.widget.attrs['class'] = TAILWIND_INPUT

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('This Student ID is already registered.')
        return student_id


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = TAILWIND_INPUT


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['student_id', 'profile_picture', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about yourself...'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = TAILWIND_INPUT
        self.fields['profile_picture'].widget = forms.FileInput(attrs={'class': TAILWIND_INPUT})
        self.fields['student_id'].required = False
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = TAILWIND_INPUT
        self.fields['profile_picture'].widget = forms.FileInput(attrs={'class': TAILWIND_INPUT})
