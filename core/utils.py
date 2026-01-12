import google.generativeai as genai
from django.conf import settings
from django.db.models import Q
from .models import Article

# Configure Gemini API
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def get_ai_response(user_message, context="", conversation_history=None):
    """Get AI response using Google Gemini API"""
    system_message = """You are a helpful AI Knowledge Assistant. Provide accurate, 
    detailed responses. When context is provided, use it to enhance your answers."""
    
    # Build the prompt with context and history
    prompt_parts = [system_message]
    
    if conversation_history:
        # Convert QuerySet to list and get last 5 messages in correct order
        history_list = list(conversation_history)
        history_list.reverse()  # Reverse to get chronological order
        recent_messages = history_list[:5]
        
        prompt_parts.append("\nConversation History:")
        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg.content}")
    
    if context:
        prompt_parts.append(f"\nContext from Knowledge Base: {context}")
    
    prompt_parts.append(f"\nUser: {user_message}")
    prompt_parts.append("\nAssistant:")
    
    full_prompt = "\n".join(prompt_parts)
    
    try:
        if not settings.GEMINI_API_KEY:
            return f"Demo mode: Received '{user_message}'. Add Gemini API key for full functionality."
        
        # FIXED: Use correct model name without 'models/' prefix
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generate response with safety settings
        generation_config = {
            'temperature': 0.7,
            'top_p': 1,
            'top_k': 1,
            'max_output_tokens': 2048,
        }
        
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        return response.text
        
    except Exception as e:
        error_msg = str(e)
        
        # If model not found, try listing available models
        if "404" in error_msg or "not found" in error_msg.lower():
            try:
                available_models = [m.name for m in genai.list_models()]
                return f"Model error. Available models: {', '.join(available_models[:5])}. Please update utils.py with a valid model name."
            except:
                return f"Error: Unable to access Gemini API. Please check your API key. Details: {error_msg}"
        
        return f"Error: {error_msg}"

def search_knowledge_base(query, limit=3):
    """Search knowledge base for relevant articles"""
    articles = Article.objects.filter(
        Q(title__icontains=query) |
        Q(content__icontains=query) |
        Q(description__icontains=query),
        is_published=True
    )[:limit]
    
    context = ""
    for article in articles:
        context += f"\n\nArticle: {article.title}\n{article.content[:500]}..."
    
    return context

def generate_conversation_title(first_message):
    """Generate title from first message"""
    words = first_message.split()[:6]
    title = ' '.join(words)
    if len(first_message.split()) > 6:
        title += '...'
    return title