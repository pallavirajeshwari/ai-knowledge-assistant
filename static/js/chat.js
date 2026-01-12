document.addEventListener('DOMContentLoaded', function () {
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const messagesContainer = document.getElementById('chatMessages');
    const newChatBtn = document.getElementById('newChatBtn');

    let currentConversationId = document.getElementById('activeConversationId')?.value;

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');

    async function createConversation() {
        try {
            console.log('Creating new conversation...');

            const response = await fetch('/api/conversation/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ title: 'New Conversation' })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to create conversation');
            }

            const data = await response.json();
            console.log('Conversation created:', data);

            currentConversationId = data.id;
            if (document.getElementById('activeConversationId')) {
                document.getElementById('activeConversationId').value = data.id;
            }

            return data;
        } catch (error) {
            console.error('Error creating conversation:', error);
            showError('Failed to create conversation: ' + error.message);
            throw error;
        }
    }

    async function sendMessage(message) {
        try {
            // Ensure we have a conversation
            if (!currentConversationId) {
                console.log('No conversation ID, creating new conversation...');
                await createConversation();
            }

            // Add user message to UI
            appendMessage('user', message);
            messageInput.value = '';

            // Show typing indicator
            showTypingIndicator();

            console.log('Sending message:', message, 'to conversation:', currentConversationId);

            const response = await fetch('/api/message/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    conversation_id: currentConversationId,
                    message: message
                })
            });

            removeTypingIndicator();

            if (!response.ok) {
                const errorData = await response.json();
                console.error('API error:', errorData);
                throw new Error(errorData.error || errorData.detail || 'Failed to send message');
            }

            const data = await response.json();
            console.log('Response received:', data);

            // Add AI response to UI
            if (data.ai_message && data.ai_message.content) {
                appendMessage('assistant', data.ai_message.content);
            } else {
                throw new Error('Invalid response format from server');
            }

        } catch (error) {
            console.error('Error sending message:', error);
            removeTypingIndicator();
            appendMessage('assistant', `Error: ${error.message}. Please check the console for details.`);
        }
    }

    function appendMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role} slide-up`;

        const userInitials = document.querySelector('.user-avatar')?.textContent || 'U';
        const aiAvatarImg = document.querySelector('.logo-icon img')?.src || '/static/images/ai.webp';

        // Parse markdown for AI messages, escape HTML for user messages
        const processedContent = role === 'assistant' ? marked.parse(content) : escapeHtml(content);

        if (role === 'user') {
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-bubble">${processedContent}</div>
                </div>
                <div class="message-avatar user-avatar-msg">${userInitials}</div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-avatar ai-avatar">
                    <img src="${aiAvatarImg}" alt="AI Avatar">
                </div>
                <div class="message-content">
                    <div class="message-bubble markdown-content">${processedContent}</div>
                </div>
            `;
        }

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'typingIndicator';
        indicator.className = 'message ai';
        
        const aiAvatarImg = document.querySelector('.logo-icon img')?.src || '/static/images/ai.webp';
        
        indicator.innerHTML = `
            <div class="message-avatar ai-avatar">
                <img src="${aiAvatarImg}" alt="AI Avatar">
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(indicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-error';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);

        setTimeout(() => {
            errorDiv.style.opacity = '0';
            setTimeout(() => errorDiv.remove(), 300);
        }, 5000);
    }

    function loadConversation(id) {
        window.location.href = `/chat/?conversation=${id}`;
    }

    if (messageForm) {
        messageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message) {
                await sendMessage(message);
            }
        });
    }

    if (messageInput) {
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                messageForm.dispatchEvent(new Event('submit'));
            }
        });

        // Auto-resize textarea
        messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', async () => {
            try {
                // Clear current conversation ID
                currentConversationId = null;
                if (document.getElementById('activeConversationId')) {
                    document.getElementById('activeConversationId').value = '';
                }
                
                // Clear the messages container
                messagesContainer.innerHTML = '';
                
                // Update chat title
                document.getElementById('chatTitle').textContent = 'New Conversation';
                
                // Show welcome message
                const aiAvatarImg = document.querySelector('.logo-icon img')?.src || '/static/images/ai.webp';
                const welcomeMsg = document.createElement('div');
                welcomeMsg.className = 'message ai';
                welcomeMsg.innerHTML = `
                    <div class="message-avatar ai-avatar">
                        <img src="${aiAvatarImg}" alt="AI Avatar">
                    </div>
                    <div class="message-content">
                        <div class="message-bubble markdown-content">
                            Hello! I'm your AI Knowledge Assistant 🤖. I can help you explore topics, answer questions, and provide insights. What would you like to know?
                        </div>
                    </div>
                `;
                messagesContainer.appendChild(welcomeMsg);
                
                // Remove active class from all conversation items
                document.querySelectorAll('.conversation-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // Focus on input
                messageInput.focus();
            } catch (error) {
                console.error('Error creating new conversation:', error);
                showError('Failed to create new conversation');
            }
        });
    }

    // Make loadConversation available globally
    window.loadConversation = loadConversation;

    console.log('Chat system initialized. Current conversation ID:', currentConversationId);
});