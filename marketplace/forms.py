from django import forms
from .models import Listing

TAILWIND_INPUT = (
    'w-full px-4 py-2 border border-stone-300 rounded-lg '
    'focus:ring-2 focus:ring-primary-500 focus:border-primary-500 '
    'dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100 '
    'dark:placeholder-slate-500 bg-stone-50 text-gray-900'
)


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'price', 'category', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': TAILWIND_INPUT}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': TAILWIND_INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = TAILWIND_INPUT


class ListingFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT,
            'placeholder': 'Search listings...',
        }),
    )
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All categories')] + Listing.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Newest first'),
            ('price_asc', 'Price: Low to High'),
            ('price_desc', 'Price: High to Low'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT}),
    )
