from django import forms

from .models import Message


class MessageForm(forms.ModelForm):
    """Server-side validation for chat messages.

    The original view wrote request.FILES['image'] straight into the model,
    which skips ImageField validation: any file type (e.g. an .html page) could
    be uploaded and later served from the application's origin. Going through
    a ModelForm runs Pillow's image check plus the extension and size
    validators declared on the model field.
    """

    content = forms.CharField(required=False, max_length=4000, strip=True)

    class Meta:
        model = Message
        fields = ['content', 'image']

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('content') and not cleaned.get('image'):
            raise forms.ValidationError('Empty message')
        return cleaned
