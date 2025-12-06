/**
 * Test Chat Page - No Authentication Required
 * 
 * Simple interface to test the Literature Agent without Supabase login.
 * Access at: http://localhost:3000/test-chat
 */

import { useState } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';

// Backend API URL
const API_URL = 'http://localhost:8000';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  agentUsed?: string;
}

interface ChatRequest {
  message: string;
  page_context: {
    route: string;
    workspace_id: string;
    user_id: string;
    experiment_ids: string[];
    protocol_ids: string[];
    filters: Record<string, unknown>;
    metadata: Record<string, unknown>;
  };
  stream: boolean;
}

interface ChatResponse {
  response: string;
  agent_used: string;
  intent: string | null;
  metadata: Record<string, unknown>;
  timestamp: string;
}

const TestChat = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: "Hello! I'm the Literature Agent. Try asking me to find research papers. Examples:\n\n• \"Find papers on CRISPR gene editing\"\n• \"Search for machine learning protein folding\"\n• \"Find recent PCR optimization protocols\"",
      role: 'assistant',
      timestamp: new Date(),
      agentUsed: 'literature_agent',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      // Build request with hardcoded test credentials
      const chatRequest: ChatRequest = {
        message: input,
        page_context: {
          route: '/test-chat',
          workspace_id: 'test-workspace',
          user_id: 'test-user',
          experiment_ids: [],
          protocol_ids: [],
          filters: {},
          metadata: { source: 'test-chat-page' },
        },
        stream: false,
      };

      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(chatRequest),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API error ${response.status}: ${errorText}`);
      }

      const data: ChatResponse = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        role: 'assistant',
        timestamp: new Date(data.timestamp),
        agentUsed: data.agent_used,
      };
      setMessages((prev) => [...prev, assistantMessage]);

    } catch (err) {
      console.error('Chat API error:', err);
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `❌ Error: ${errorMsg}\n\nMake sure the backend is running:\nuvicorn backend.main:app --reload --port 8000`,
        role: 'assistant',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
              <Bot className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Literature Agent Test
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                SpoonOS Backend • No Auth Required
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Container */}
      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          {/* Messages */}
          <div className="h-[500px] overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center flex-shrink-0">
                    <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                  }`}
                >
                  <pre className="whitespace-pre-wrap font-sans text-sm">
                    {msg.content}
                  </pre>
                  {msg.agentUsed && (
                    <p className="text-xs mt-2 opacity-70">
                      Agent: {msg.agentUsed}
                    </p>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center flex-shrink-0">
                    <User className="h-4 w-4 text-gray-600 dark:text-gray-300" />
                  </div>
                )}
              </div>
            ))}
            
            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Searching literature...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t dark:border-gray-700 p-4">
            {error && (
              <div className="mb-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-600 dark:text-red-400">
                  Connection error. Is the backend running on port 8000?
                </p>
              </div>
            )}
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask about research papers... (e.g., 'Find CRISPR papers')"
                disabled={isLoading}
                className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
          Backend: {API_URL} • Workspace: test-workspace • User: test-user
        </div>
      </main>
    </div>
  );
};

export default TestChat;
