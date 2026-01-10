from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Category, Article

class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **kwargs):
        # Create superuser if not exists
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Superuser created: admin/admin123'))

        # Create categories
        categories_data = [
            {'name': 'Artificial Intelligence', 'icon': '🤖', 'color': 'icon-orange'},
            {'name': 'Quantum Computing', 'icon': '⚡', 'color': 'icon-teal'},
            {'name': 'Climate Science', 'icon': '🌍', 'color': 'icon-green'},
            {'name': 'Space Technology', 'icon': '🚀', 'color': 'icon-purple'},
            {'name': 'Biotechnology', 'icon': '🧬', 'color': 'icon-pink'},
            {'name': 'Renewable Energy', 'icon': '💡', 'color': 'icon-yellow'},
        ]
        
        for cat_data in categories_data:
            Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon': cat_data['icon'],
                    'color': cat_data['color'],
                    'description': f'Learn about {cat_data["name"].lower()}'
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Categories created'))

        # Create sample articles
        admin_user = User.objects.get(username='admin')
        ai_category = Category.objects.get(name='Artificial Intelligence')
        
        articles_data = [
            {
                'title': 'Understanding Large Language Models',
                'category': ai_category,
                'description': 'Explore the architecture and capabilities of modern large language models like GPT, their training processes, and real-world applications transforming industries.',
                'content': '''Large Language Models (LLMs) represent a breakthrough in artificial intelligence. These models are trained on vast amounts of text data and can understand and generate human-like text.

Key Components:
- Transformer Architecture: The foundation of modern LLMs
- Attention Mechanisms: Allow the model to focus on relevant parts of the input
- Pre-training and Fine-tuning: Two-stage training process
- Tokenization: Converting text into numerical representations

Applications:
- Content generation and creative writing
- Code generation and debugging
- Translation and summarization
- Question answering and information retrieval
- Conversational AI and chatbots

The impact of LLMs extends across industries, from healthcare to education, finance to entertainment. As these models continue to evolve, they promise to revolutionize how we interact with technology and process information.''',
                'read_time': 12
            },
            {
                'title': 'Neural Networks Deep Dive',
                'category': ai_category,
                'description': 'A comprehensive guide to understanding neural networks, from basic perceptrons to deep learning architectures.',
                'content': '''Neural networks are computational models inspired by the human brain. They consist of layers of interconnected nodes (neurons) that process information.

Basic Structure:
- Input Layer: Receives raw data
- Hidden Layers: Process and transform data
- Output Layer: Produces final results
- Weights and Biases: Learned parameters

Types of Neural Networks:
1. Feedforward Networks: Simple, unidirectional flow
2. Convolutional Neural Networks (CNNs): Image processing
3. Recurrent Neural Networks (RNNs): Sequential data
4. Transformers: State-of-the-art for NLP

Training Process:
- Forward propagation
- Loss calculation
- Backpropagation
- Gradient descent optimization

Modern applications include computer vision, natural language processing, autonomous vehicles, and medical diagnosis.''',
                'read_time': 15
            }
        ]
        
        for article_data in articles_data:
            Article.objects.get_or_create(
                title=article_data['title'],
                defaults={
                    **article_data,
                    'author': admin_user,
                    'is_published': True
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Sample articles created'))
        self.stdout.write(self.style.SUCCESS('Sample data creation complete!'))