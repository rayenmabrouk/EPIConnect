from django import forms
from .models import Item

TAILWIND_INPUT = (
    'w-full px-4 py-2 border border-stone-300 rounded-lg '
    'focus:ring-2 focus:ring-primary-500 focus:border-primary-500 '
    'dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100 '
    'dark:placeholder-slate-500 bg-stone-50 text-gray-900'
)


class ItemForm(forms.ModelForm):
    item_type = forms.ChoiceField(
        choices=[('lost', 'I lost something'), ('found', 'I found something')],
        widget=forms.RadioSelect(attrs={'class': 'mr-2'}),
        initial='lost',
    )

    class Meta:
        model = Item
        fields = ['title', 'description', 'image', 'location', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': TAILWIND_INPUT}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': TAILWIND_INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('item_type',):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = TAILWIND_INPUT


class ItemFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT,
            'placeholder': 'Search by title or description...',
        }),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All statuses')] + Item.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
    )
