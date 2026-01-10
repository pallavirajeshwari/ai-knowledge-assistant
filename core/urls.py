from django.urls import path
from . import views

urlpatterns = [
    # Home & Authentication
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # OTP Email Verification Routes
    path('verify-otp/<str:email>/', views.verify_otp, name='verify_otp'),
    path('resend-otp/<str:email>/', views.resend_otp, name='resend_otp'),
    
    # Main Dashboard & Features
    path('dashboard/', views.dashboard, name='dashboard'),
    path('chat/', views.chat_view, name='chat'),
    path('settings/', views.settings_view, name='settings'),
    
    # Knowledge Base
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('articles/', views.knowledge_base, name='articles'),
    path('article/<slug:slug>/', views.article_detail, name='article_detail'),
    
    # Contact/Enquiry Routes
    path('contact/', views.contact_view, name='contact'),
    path('contact/success/', views.contact_success_view, name='contact_success'),
    
    # Chat API Endpoints
    path('api/conversations/', views.list_conversations, name='api_list_conversations'),
    path('api/conversation/create/', views.create_conversation, name='api_create_conversation'),
    path('api/conversation/<int:conversation_id>/', views.get_conversation_messages, name='api_get_messages'),
    path('api/conversation/<int:conversation_id>/delete/', views.delete_conversation, name='api_delete_conversation'),
    path('api/message/send/', views.send_message, name='api_send_message'),
    
    # Settings & Notifications API
    path('api/settings/update/', views.update_settings, name='api_update_settings'),
    path('api/notifications/clear/', views.clear_notifications, name='api_clear_notifications'),
    path('api/notification/<int:notification_id>/read/', views.mark_notification_read, name='api_mark_notification_read'),
]