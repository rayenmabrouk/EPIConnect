from django.core.validators import MinValueValidator
from django.db import models

from core.validators import IMAGE_VALIDATORS, RandomFilename
from django.conf import settings


class Listing(models.Model):
    CATEGORY_CHOICES = [
        ('books', 'Books'),
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('furniture', 'Furniture'),
        ('services', 'Services'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    image = models.ImageField(
        upload_to=RandomFilename('marketplace'), blank=True, null=True, validators=IMAGE_VALIDATORS,
    )
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
