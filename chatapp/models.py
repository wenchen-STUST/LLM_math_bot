from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.user.username


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_sessions')
    title = models.CharField(max_length=255, default='新對話')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    summary = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)
    content = models.TextField()
    model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class ImageCache(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='cached_images')
    prompt_hash = models.CharField(max_length=64, db_index=True)
    image_data = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Cache: {self.prompt_hash[:16]}..."


class UsageStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='usage_stats')
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, null=True, blank=True, related_name='usage_stats')
    model_name = models.CharField(max_length=100)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    message_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user}: {self.model_name} - {self.message_count} msgs"
