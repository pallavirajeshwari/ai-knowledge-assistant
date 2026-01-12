from django.contrib import admin
from .models import Category, Article, Conversation, Message, UserProfile, Notification, UserSettings, Enquiry,EmailOTP

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'color', 'created_at']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'read_time', 'views', 'is_published']
    list_filter = ['category', 'is_published', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    
    # Set default value for is_published when creating new articles
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Only for new articles (not editing existing ones)
            form.base_fields['is_published'].initial = True
        return form
    
    # Add bulk actions to publish/unpublish articles
    def publish_articles(self, request, queryset):
        queryset.update(is_published=True)
        self.message_user(request, f'{queryset.count()} article(s) published.')
    publish_articles.short_description = "Publish selected articles"
    
    def unpublish_articles(self, request, queryset):
        queryset.update(is_published=False)
        self.message_user(request, f'{queryset.count()} article(s) unpublished.')
    unpublish_articles.short_description = "Unpublish selected articles"
    
    actions = ['publish_articles', 'unpublish_articles']
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'created_at']
    list_filter = ['created_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'timestamp']
    list_filter = ['role', 'timestamp']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_conversations', 'total_messages', 'joined_date']
    search_fields = ['user__username', 'user__email']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected notifications as unread"
    
    actions = ['mark_as_read', 'mark_as_unread']

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'article_alerts', 'chat_notifications', 'dark_mode']
    list_filter = ['email_notifications', 'article_alerts', 'chat_notifications', 'dark_mode']
    search_fields = ['user__username', 'user__email']

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'status', 'created_at', 'user']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('user', 'name', 'email', 'phone')
        }),
        ('Enquiry Details', {
            'fields': ('subject', 'message', 'status')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
    mark_as_in_progress.short_description = "Mark as In Progress"
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
    mark_as_resolved.short_description = "Mark as Resolved"
    
    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
    mark_as_closed.short_description = "Mark as Closed"
    
    actions = ['mark_as_in_progress', 'mark_as_resolved', 'mark_as_closed']

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'otp', 'is_verified', 'attempts', 'created_at', 'is_expired_status']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['email', 'username']
    readonly_fields = ['created_at', 'otp']
    ordering = ['-created_at']
    
    def is_expired_status(self, obj):
        return '✓ Valid' if not obj.is_expired() else '✗ Expired'
    is_expired_status.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation
    
    actions = ['delete_expired_otps']
    
    def delete_expired_otps(self, request, queryset):
        count = 0
        for otp in queryset:
            if otp.is_expired():
                otp.delete()
                count += 1
        self.message_user(request, f'{count} expired OTP(s) deleted.')
    delete_expired_otps.short_description = 'Delete expired OTPs'