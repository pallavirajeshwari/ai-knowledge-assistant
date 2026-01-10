from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Conversation, Message, Article, Category, UserProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'timestamp']

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'preview', 'created_at', 'updated_at', 'messages', 'message_count']
    
    def get_message_count(self, obj):
        return obj.messages.count()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color']

class ArticleSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'category', 'description', 'content', 
                  'author', 'read_time', 'views', 'created_at', 'updated_at']