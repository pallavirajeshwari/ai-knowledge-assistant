import google.generativeai as genai
from django.conf import settings

class ChatService:
    def __init__(self):
        """Initialize Gemini AI client (FREE API)"""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def get_ai_response(self, user_message, context=None, conversation_history=None):
        """
        Get response from Google Gemini API (FREE)
        
        Args:
            user_message: The current user message
            context: Knowledge base context (optional)
            conversation_history: List of previous Message objects (optional)
        
        Returns:
            AI response text
        """
        # Build the prompt
        prompt = "You are a helpful AI assistant with access to a knowledge base. Provide accurate, helpful, and friendly responses.\n\n"
        
        # Add context from knowledge base if provided
        if context:
            prompt += f"Relevant information from knowledge base:\n{context}\n\n"
        
        # Add conversation history if provided (last 5 messages to save tokens)
        if conversation_history:
            prompt += "Previous conversation:\n"
            for msg in conversation_history[-5:]:
                role = "User" if msg.role == "user" else "Assistant"
                prompt += f"{role}: {msg.content}\n"
            prompt += "\n"
        
        # Add current user message
        prompt += f"User: {user_message}\nAssistant:"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            print(f"Gemini API Error: {str(e)}")
            raise Exception(f"Error calling Gemini API: {str(e)}")