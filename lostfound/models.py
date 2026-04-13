from django.db import models
from django.conf import settings


class Item(models.Model):
    STATUS_CHOICES = [
        ('lost', 'Lost'),
        ('found', 'Found'),
        ('claimed', 'Claimed'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='lostfound/', blank=True, null=True)
    location = models.CharField(max_length=255)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='lost')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lostfound_items')
    finder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='found_items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"


class ItemHistory(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('status_changed', 'Status Changed'),
        ('message_sent', 'Message Sent'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Item histories'

    def __str__(self):
        return f"{self.item.title} - {self.action}"
