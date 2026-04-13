from django import forms
from .models import Post, Comment

TAILWIND_INPUT = (
    'w-full px-4 py-2 border border-stone-300 rounded-lg '
    'focus:ring-2 focus:ring-primary-500 focus:border-primary-500 '
    'dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100 '
    'dark:placeholder-slate-500 bg-stone-50 text-gray-900'
)


class PostForm(forms.ModelForm):
    is_anonymous = forms.BooleanField(
        required=False,
        label='Post anonymously',
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500',
        }),
    )

    class Meta:
        model = Post
        fields = ['content', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'class': TAILWIND_INPUT,
                'placeholder': 'Ask for help, share a tip, or start a discussion...',
            }),
        }


class CommentForm(forms.ModelForm):
    is_anonymous = forms.BooleanField(
        required=False,
        label='Comment anonymously',
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500',
        }),
    )

    class Meta:
        model = Comment
        fields = ['content', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'class': TAILWIND_INPUT,
                'placeholder': 'Write a comment...',
            }),
        }
