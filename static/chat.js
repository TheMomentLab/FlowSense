(function() {
    'use strict';

    var chatFab = document.getElementById('chatFab');
    var chatPanel = document.getElementById('chatPanel');
    var chatClose = document.getElementById('chatClose');
    var chatMessages = document.getElementById('chatMessages');
    var chatInput = document.getElementById('chatInput');
    var chatSend = document.getElementById('chatSend');
    var chatOpen = false;
    var activeEventSource = null;

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }

    function renderMarkdown(text) {
        var escaped = escapeHtml(text);
        return escaped
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    function toggleChat() {
        chatOpen = !chatOpen;
        if (chatOpen) {
            chatPanel.classList.add('open');
            chatFab.classList.add('hidden');
            chatInput.focus();
        } else {
            chatPanel.classList.remove('open');
            chatFab.classList.remove('hidden');
            if (activeEventSource) {
                activeEventSource.close();
                activeEventSource = null;
            }
        }
    }

    function addMessage(role, content) {
        var div = document.createElement('div');
        div.className = 'chat-message ' + role;
        if (role === 'assistant') {
            div.innerHTML = renderMarkdown(content);
        } else {
            div.textContent = content;
        }
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return div;
    }

    function getCurrentStock() {
        if (typeof window.currentStockName === 'string' && window.currentStockName) {
            return window.currentStockName;
        }
        var el = document.getElementById('stockName');
        if (el && el.textContent) return el.textContent;
        return '';
    }

    function sendChat() {
        var msg = chatInput.value.trim();
        if (!msg) return;

        chatInput.value = '';
        chatSend.disabled = true;
        addMessage('user', msg);

        var aiDiv = addMessage('assistant', '');
        var aiText = '';

        var stock = getCurrentStock();
        var url = '/api/chat?message=' + encodeURIComponent(msg);
        if (stock) url += '&stock=' + encodeURIComponent(stock);

        if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
        }

        try {
            var eventSource = new EventSource(url);
            activeEventSource = eventSource;

            eventSource.onmessage = function(e) {
                try {
                    var data = JSON.parse(e.data);

                    if (data.done) {
                        eventSource.close();
                        activeEventSource = null;
                        aiDiv.innerHTML = renderMarkdown(aiText);
                        chatSend.disabled = false;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        return;
                    }

                    if (data.error) {
                        eventSource.close();
                        activeEventSource = null;
                        aiDiv.textContent = data.error;
                        aiDiv.classList.add('chat-error-msg');
                        chatSend.disabled = false;
                        return;
                    }

                    if (data.text) {
                        aiText += data.text;
                        aiDiv.innerHTML = renderMarkdown(aiText);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                } catch (err) {
                    // ignore SSE parse errors
                }
            };

            eventSource.onerror = function() {
                eventSource.close();
                activeEventSource = null;
                if (!aiText) {
                    aiDiv.textContent = '연결 오류가 발생했습니다.';
                    aiDiv.classList.add('chat-error-msg');
                } else {
                    aiDiv.innerHTML = renderMarkdown(aiText);
                }
                chatSend.disabled = false;
            };
        } catch (err) {
            aiDiv.textContent = '요청 중 오류가 발생했습니다.';
            aiDiv.classList.add('chat-error-msg');
            chatSend.disabled = false;
        }
    }

    chatFab.addEventListener('click', toggleChat);
    chatClose.addEventListener('click', toggleChat);
    chatSend.addEventListener('click', sendChat);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendChat();
    });
})();
