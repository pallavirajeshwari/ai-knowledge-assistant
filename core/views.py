from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
import json
import os
import random
import string
import threading

from .models import Article, Category, Conversation, Message, UserProfile, Notification, UserSettings, Enquiry, EmailOTP
from .forms import SignUpForm, LoginForm, EnquiryForm
from .utils import get_ai_response, search_knowledge_base, generate_conversation_title

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/index.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()
    
    return render(request, 'core/login.html', {'form': form})


# ============================================
# UPDATED SIGNUP WITH OTP VERIFICATION
# ============================================

def signup_view(request):
    """Step 1: Collect user details and create account (skip OTP in production)"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Extract form data
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data.get('first_name', '')
            last_name = form.cleaned_data.get('last_name', '')
            password = form.cleaned_data['password1']
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists!')
                return render(request, 'core/signup.html', {'form': form})
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered!')
                return render(request, 'core/signup.html', {'form': form})
            
            # PRODUCTION MODE: Skip email verification
            if not settings.DEBUG:
                try:
                    with transaction.atomic():
                        # Create user directly
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            first_name=first_name,
                            last_name=last_name
                        )
                        
                        # Create user profile
                        profile, created = UserProfile.objects.get_or_create(user=user)
                        
                        # Create user settings
                        settings_obj, created = UserSettings.objects.get_or_create(user=user)
                        
                        # Create welcome notification
                        Notification.objects.create(
                            user=user,
                            title="Welcome to AI Assistant! 🎉",
                            message="Get started by exploring our knowledge base or starting a new conversation.",
                            notification_type='welcome'
                        )
                        
                        # Log the user in automatically
                        login(request, user)
                        
                        messages.success(request, f'🎉 Account created successfully! Welcome aboard, {first_name or username}!')
                        return redirect('dashboard')
                        
                except IntegrityError:
                    messages.error(request, '❌ Account creation failed. Username or email may already exist.')
                    return render(request, 'core/signup.html', {'form': form})
                except Exception as e:
                    messages.error(request, f'❌ Error creating account: {str(e)}')
                    return render(request, 'core/signup.html', {'form': form})
            
            # DEVELOPMENT MODE: Use OTP verification
            else:
                # Delete any existing OTP for this email
                EmailOTP.objects.filter(email=email).delete()
                
                # Create new OTP record
                otp_record = EmailOTP.objects.create(
                    email=email,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    password=make_password(password)  # Store hashed password
                )
                
                # Send OTP email (non-blocking)
                try:
                    send_otp_email(email, otp_record.otp)
                    messages.success(request, f'✉️ OTP sent to {email}. Please check your inbox.')
                    return redirect('verify_otp', email=email)
                except Exception as e:
                    # Don't delete OTP record, just warn user
                    print(f"Email queuing: {e}")
                    messages.success(request, f'✉️ OTP is being sent to {email}. Please check your inbox in a moment.')
                    return redirect('verify_otp', email=email)
    else:
        form = SignUpForm()
    
    return render(request, 'core/signup.html', {'form': form})


def verify_otp(request, email):
    """Step 2: Verify OTP and create user account"""
    try:
        otp_record = EmailOTP.objects.get(email=email, is_verified=False)
    except EmailOTP.DoesNotExist:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect('signup')
    
    # Check if OTP is expired
    if otp_record.is_expired():
        messages.error(request, '⏱️ OTP has expired. Please signup again.')
        otp_record.delete()
        return redirect('signup')
    
    # Check if account is locked
    if otp_record.is_locked():
        messages.error(request, '🔒 Too many failed attempts. Please signup again.')
        otp_record.delete()
        return redirect('signup')
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        
        if entered_otp == otp_record.otp:
            # OTP is correct - create user account with transaction
            try:
                with transaction.atomic():
                    # Check if user already exists (double-check)
                    if User.objects.filter(username=otp_record.username).exists():
                        messages.error(request, '❌ Username already exists. Please signup with a different username.')
                        otp_record.delete()
                        return redirect('signup')
                    
                    if User.objects.filter(email=otp_record.email).exists():
                        messages.error(request, '❌ Email already registered. Please login or use a different email.')
                        otp_record.delete()
                        return redirect('signup')
                    
                    # Create user
                    user = User.objects.create(
                        username=otp_record.username,
                        email=otp_record.email,
                        first_name=otp_record.first_name,
                        last_name=otp_record.last_name,
                        password=otp_record.password  # Already hashed
                    )
                    
                    # Mark OTP as verified BEFORE creating profile
                    otp_record.is_verified = True
                    otp_record.save()
                    
                    # Create user profile (with get_or_create to prevent duplicates)
                    profile, created = UserProfile.objects.get_or_create(user=user)
                    
                    # Create user settings (with get_or_create to prevent duplicates)
                    settings_obj, created = UserSettings.objects.get_or_create(user=user)
                    
                    # Create welcome notification
                    Notification.objects.create(
                        user=user,
                        title="Welcome to AI Assistant! 🎉",
                        message="Get started by exploring our knowledge base or starting a new conversation.",
                        notification_type='welcome'
                    )
                    
                    # Log the user in
                    login(request, user)
                    
                    messages.success(request, f'🎉 Account created successfully! Welcome aboard, {user.first_name or user.username}!')
                    
                    # Delete OTP record after successful registration
                    otp_record.delete()
                    
                    return redirect('dashboard')
                    
            except IntegrityError as e:
                # Handle any database integrity errors
                messages.error(request, f'❌ Account creation failed. This username or email may already exist. Please try again.')
                # Delete the OTP record so user can restart
                otp_record.delete()
                return redirect('signup')
            except Exception as e:
                messages.error(request, f'❌ Error creating account: {str(e)}')
                return render(request, 'core/verify_otp.html', {'email': email})
        else:
            # Wrong OTP
            otp_record.attempts += 1
            otp_record.save()
            
            remaining_attempts = 5 - otp_record.attempts
            if remaining_attempts > 0:
                messages.error(request, f'❌ Invalid OTP. {remaining_attempts} attempt(s) remaining.')
            else:
                messages.error(request, '🔒 Too many failed attempts. Please signup again.')
                otp_record.delete()
                return redirect('signup')
    
    return render(request, 'core/verify_otp.html', {'email': email})


def resend_otp(request, email):
    """Resend OTP to email"""
    try:
        otp_record = EmailOTP.objects.get(email=email, is_verified=False)
        
        # Check if OTP is expired
        if otp_record.is_expired():
            messages.error(request, '⏱️ Session expired. Please signup again.')
            otp_record.delete()
            return redirect('signup')
        
        # Generate new OTP
        new_otp = EmailOTP.generate_otp()
        otp_record.otp = new_otp
        otp_record.attempts = 0  # Reset attempts
        otp_record.save()
        
        # Send new OTP (non-blocking)
        try:
            send_otp_email(email, new_otp)
            messages.success(request, '✉️ New OTP sent to your email!')
        except Exception as e:
            print(f"Email queuing: {e}")
            messages.success(request, '✉️ New OTP is being sent to your email!')
        
        return redirect('verify_otp', email=email)
    except EmailOTP.DoesNotExist:
        messages.error(request, 'Invalid request. Please signup again.')
        return redirect('signup')


def send_otp_email(email, otp):
    """Send OTP email to user - non-blocking with threading"""
    
    def send_email_in_background():
        """Background thread for email sending"""
        try:
            subject = '🔐 Verify Your Email - AI Knowledge Assistant'
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 40px 30px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 28px; }}
                    .icon {{ font-size: 48px; margin-bottom: 15px; }}
                    .content {{ padding: 40px 30px; text-align: center; }}
                    .content h2 {{ color: #111827; font-size: 24px; margin-bottom: 20px; }}
                    .content p {{ color: #6b7280; line-height: 1.6; margin-bottom: 30px; }}
                    .otp-box {{ background: linear-gradient(135deg, #f3f4f6, #e5e7eb); border: 3px dashed #667eea; border-radius: 12px; padding: 30px; margin: 30px 0; font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 10px; }}
                    .info-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin: 30px 0; text-align: left; }}
                    .info-box p {{ margin: 5px 0; color: #92400e; font-size: 14px; }}
                    .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="icon">🤖</div>
                        <h1>AI Knowledge Assistant</h1>
                    </div>
                    <div class="content">
                        <h2>Email Verification</h2>
                        <p>Thank you for signing up! Use the OTP below to complete registration:</p>
                        <div class="otp-box">{otp}</div>
                        <div class="info-box">
                            <p><strong>⏱️ Valid for 10 minutes</strong></p>
                            <p>🔒 Don't share this code</p>
                            <p>❓ Didn't request? Ignore this email</p>
                        </div>
                    </div>
                    <div class="footer">
                        <p><strong>AI Knowledge Assistant</strong></p>
                        <p>&copy; 2024 Your intelligent learning companion</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            plain_message = f"""
AI Knowledge Assistant - Email Verification

Your OTP: {otp}

Valid for 10 minutes. Enter this on the verification page.

Don't share this code with anyone.
If you didn't request this, ignore this email.

---
AI Knowledge Assistant
            """
            
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            email_msg.attach_alternative(html_message, "text/html")
            email_msg.send(fail_silently=False)
            
            print(f"✅ OTP email sent successfully to {email}")
            
        except Exception as e:
            print(f"❌ Email send failed for {email}: {str(e)}")
    
    # Start background thread - won't block request
    thread = threading.Thread(target=send_email_in_background)
    thread.daemon = True
    thread.start()
    
    print(f"📧 Email queued for {email}")


# ============================================
# REST OF THE VIEWS (UNCHANGED)
# ============================================

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('index')

@login_required
def dashboard(request):
    profile = request.user.profile
    recent_conversations = Conversation.objects.filter(user=request.user)[:5]
    recent_articles = Article.objects.filter(is_published=True)[:6]
    
    context = {
        'profile': profile,
        'recent_conversations': recent_conversations,
        'recent_articles': recent_articles,
        'total_articles': Article.objects.filter(is_published=True).count(),
        'user_conversations': Conversation.objects.filter(user=request.user).count(),
        'articles_read': profile.articles_read.count(),
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def chat_view(request):
    conversations = Conversation.objects.filter(user=request.user)
    active_conversation = conversations.first() if conversations.exists() else None
    
    return render(request, 'core/chat.html', {
        'conversations': conversations,
        'active_conversation': active_conversation,
    })

@login_required
def settings_view(request):
    profile = request.user.profile
    user_settings = profile
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'remove_avatar':
            if profile.avatar:
                try:
                    avatar_path = profile.avatar.path
                    if os.path.isfile(avatar_path):
                        os.remove(avatar_path)
                except Exception as e:
                    print(f"Error deleting avatar file: {e}")
                
                profile.avatar.delete(save=False)
                profile.avatar = None
                profile.save()
                
                messages.success(request, '✅ Avatar removed successfully!')
            else:
                messages.info(request, 'No avatar to remove.')
            
            return redirect('settings')
        
        elif form_type == 'profile':
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.save()
            
            profile.bio = request.POST.get('bio', '').strip()
            
            if request.FILES.get('avatar'):
                if profile.avatar:
                    try:
                        old_avatar_path = profile.avatar.path
                        if os.path.isfile(old_avatar_path):
                            os.remove(old_avatar_path)
                    except Exception as e:
                        print(f"Error deleting old avatar: {e}")
                
                profile.avatar = request.FILES['avatar']
            
            profile.save()
            messages.success(request, '✅ Profile updated successfully!')
            return redirect('settings')
        
        elif form_type == 'password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            if not current_password or not new_password:
                messages.error(request, '❌ Please fill in all password fields!')
            elif not check_password(current_password, request.user.password):
                messages.error(request, '❌ Current password is incorrect!')
            elif new_password != confirm_password:
                messages.error(request, '❌ New passwords do not match!')
            elif len(new_password) < 8:
                messages.error(request, '❌ Password must be at least 8 characters!')
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, '✅ Password updated successfully!')
            
            return redirect('settings')
    
    context = {
        'profile': profile,
        'user_settings': user_settings,
        'notifications': Notification.objects.filter(user=request.user).order_by('-created_at')[:5],
        'user_conversations': Conversation.objects.filter(user=request.user).count(),
    }
    
    return render(request, 'core/settings.html', context)

@login_required
def knowledge_base(request):
    categories = Category.objects.all()
    articles = Article.objects.filter(is_published=True)
    
    if request.GET.get('category'):
        articles = articles.filter(category__slug=request.GET.get('category'))
    
    if request.GET.get('q'):
        query = request.GET.get('q')
        articles = articles.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(content__icontains=query)
        )
    
    return render(request, 'core/knowledge_base.html', {
        'categories': categories,
        'articles': articles,
        'search_query': request.GET.get('q', ''),
    })

@login_required
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    article.views += 1
    article.save()
    
    request.user.profile.articles_read.add(article)
    
    try:
        user_settings = request.user.settings
        if user_settings.article_alerts:
            Notification.objects.create(
                user=request.user,
                title=f"You read: {article.title}",
                message=f"You've completed reading this article. Check out related articles in {article.category.name}.",
                notification_type='article'
            )
    except UserSettings.DoesNotExist:
        pass
    
    related_articles = Article.objects.filter(
        category=article.category,
        is_published=True
    ).exclude(id=article.id)[:3]
    
    return render(request, 'core/article_detail.html', {
        'article': article,
        'related_articles': related_articles,
    })

def contact_view(request):
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save(commit=False)
            
            if request.user.is_authenticated:
                enquiry.user = request.user
            
            enquiry.save()
            
            try:
                send_enquiry_emails(enquiry)
                messages.success(request, 'Your enquiry has been submitted successfully! We will get back to you soon.')
            except Exception as e:
                messages.warning(request, 'Your enquiry has been submitted, but there was an issue sending the confirmation email.')
                print(f"Email error: {e}")
            
            return redirect('contact_success')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                'email': request.user.email,
            }
        form = EnquiryForm(initial=initial_data)
    
    return render(request, 'core/contact.html', {'form': form})

def contact_success_view(request):
    return render(request, 'core/contact_success.html')

def send_enquiry_emails(enquiry):
    admin_subject = f'New Enquiry: {enquiry.subject}'
    admin_context = {
        'enquiry': enquiry,
        'admin_url': f"{settings.SITE_URL}/admin/core/enquiry/{enquiry.id}/change/" if hasattr(settings, 'SITE_URL') else ''
    }
    admin_html_message = render_to_string('core/emails/enquiry_admin.html', admin_context)
    admin_plain_message = strip_tags(admin_html_message)
    
    admin_email = EmailMultiAlternatives(
        subject=admin_subject,
        body=admin_plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.ADMIN_EMAIL],
    )
    admin_email.attach_alternative(admin_html_message, "text/html")
    admin_email.send(fail_silently=False)
    
    user_subject = f'We received your enquiry: {enquiry.subject}'
    user_context = {
        'enquiry': enquiry,
        'support_email': settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else settings.DEFAULT_FROM_EMAIL
    }
    user_html_message = render_to_string('core/emails/enquiry_confirmation.html', user_context)
    user_plain_message = strip_tags(user_html_message)
    
    user_email = EmailMultiAlternatives(
        subject=user_subject,
        body=user_plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[enquiry.email],
    )
    user_email.attach_alternative(user_html_message, "text/html")
    user_email.send(fail_silently=False)

@login_required
@require_http_methods(["POST"])
def create_conversation(request):
    try:
        data = json.loads(request.body)
        conversation = Conversation.objects.create(
            user=request.user,
            title=data.get('title', 'New Conversation')
        )
        request.user.profile.total_conversations += 1
        request.user.profile.save()
        
        return JsonResponse({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def send_message(request):
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        user_message = data.get('message')
        
        if not conversation_id or not user_message:
            return JsonResponse({'error': 'Invalid request'}, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        
        user_msg = Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message
        )
        
        history = Message.objects.filter(conversation=conversation).order_by('-timestamp')[:10]
        context = search_knowledge_base(user_message)
        ai_response = get_ai_response(user_message, context, history)
        
        ai_msg = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=ai_response
        )
        
        if conversation.message_count() == 2:
            conversation.title = generate_conversation_title(user_message)
        conversation.preview = user_message[:100]
        conversation.save()
        
        request.user.profile.total_messages += 2
        request.user.profile.save()
        
        try:
            user_settings = request.user.settings
            if user_settings.chat_notifications:
                Notification.objects.create(
                    user=request.user,
                    title="AI Response Received",
                    message=f"Your question about '{user_message[:50]}...' has been answered.",
                    notification_type='chat'
                )
        except UserSettings.DoesNotExist:
            pass
        
        return JsonResponse({
            'user_message': {
                'id': user_msg.id,
                'role': user_msg.role,
                'content': user_msg.content,
                'timestamp': user_msg.timestamp.isoformat()
            },
            'ai_message': {
                'id': ai_msg.id,
                'role': ai_msg.role,
                'content': ai_msg.content,
                'timestamp': ai_msg.timestamp.isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["GET"])
def get_conversation_messages(request, conversation_id):
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        messages_data = [
            {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat()
            }
            for msg in conversation.messages.all()
        ]
        
        return JsonResponse({
            'id': conversation.id,
            'title': conversation.title,
            'messages': messages_data
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["GET"])
def list_conversations(request):
    try:
        conversations = Conversation.objects.filter(user=request.user)
        conversations_data = [
            {
                'id': conv.id,
                'title': conv.title,
                'preview': conv.preview,
                'created_at': conv.created_at.isoformat()
            }
            for conv in conversations
        ]
        return JsonResponse({'conversations': conversations_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["DELETE"])
def delete_conversation(request, conversation_id):
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        conversation.delete()
        return JsonResponse({'message': 'Deleted'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def update_settings(request):
    try:
        data = json.loads(request.body)
        user_settings, created = UserSettings.objects.get_or_create(user=request.user)
        
        setting_type = data.get('type')
        value = data.get('value')
        
        if setting_type == 'email_notifications':
            user_settings.email_notifications = value
        elif setting_type == 'article_alerts':
            user_settings.article_alerts = value
        elif setting_type == 'chat_notifications':
            user_settings.chat_notifications = value
        elif setting_type == 'dark_mode':
            user_settings.dark_mode = value
            
        user_settings.save()
        
        return JsonResponse({'success': True, 'message': 'Settings updated'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def clear_notifications(request):
    try:
        Notification.objects.filter(user=request.user).delete()
        return JsonResponse({'success': True, 'message': 'All notifications cleared'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)