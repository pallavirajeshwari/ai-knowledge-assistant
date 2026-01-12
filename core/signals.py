from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, UserSettings

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile and UserSettings when a new User is created"""
    if created:
        # Use get_or_create to prevent duplicates in case of race conditions
        UserProfile.objects.get_or_create(user=instance)
        UserSettings.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure profile and settings exist whenever user is saved"""
    # Don't try to save during user creation (handled above)
    if not kwargs.get('created', False):
        # Ensure profile and settings exist
        UserProfile.objects.get_or_create(user=instance)
        UserSettings.objects.get_or_create(user=instance)