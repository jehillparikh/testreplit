document.addEventListener('DOMContentLoaded', function() {
    const chatbotWidget = document.getElementById('chatbotWidget');
    const chatbotTrigger = document.getElementById('chatbotTrigger');
    const minimizeChatbot = document.getElementById('minimizeChatbot');
    const chatMessages = document.getElementById('chatMessages');
    
    // Toggle chatbot visibility
    chatbotTrigger.addEventListener('click', () => {
        chatbotWidget.style.display = 'flex';
        chatbotTrigger.style.display = 'none';
    });
    
    minimizeChatbot.addEventListener('click', () => {
        chatbotWidget.style.display = 'none';
        chatbotTrigger.style.display = 'block';
    });
    
    // Handle message sending
    window.sendMessage = function(event) {
        event.preventDefault();
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (message) {
            addMessage(message, 'user');
            processMessage(message);
            messageInput.value = '';
        }
    };
    
    // Handle quick action questions
    window.askQuestion = function(question) {
        addMessage(question, 'user');
        processMessage(question);
    };
    
    function addMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    async function processMessage(message) {
        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot typing';
        typingDiv.textContent = 'Typing...';
        chatMessages.appendChild(typingDiv);
        
        try {
            const response = await fetch('/api/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            chatMessages.removeChild(typingDiv);
            
            // Add bot response
            addMessage(data.response, 'bot');
            
        } catch (error) {
            console.error('Error:', error);
            chatMessages.removeChild(typingDiv);
            addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
    }
});
