import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Send, Bot, Search, Mic, MicOff, Paperclip, Globe, Copy, Volume2, VolumeX, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useVoice } from '@/hooks/useVoice';

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

export const AIAssistantChat = () => {
  const location = useLocation();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: "Hello! I'm 12Record, your AI research assistant. I'm powered by the SpoonOS framework. How can I help you today?",
      role: 'assistant',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const lastAgentRef = useRef<string | undefined>(undefined);

  // Voice hook
  const {
    isAvailable: isVoiceAvailable,
    isEnabled: isVoiceEnabled,
    toggleVoice,
    isSpeaking,
    isListening,
    speak,
    stopSpeaking,
    listen,
    isSTTSupported,
  } = useVoice({
    onError: (error) => {
      console.error('[AIAssistantChat] Voice error:', error.message);
    },
  });

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Build request payload
      const chatRequest: ChatRequest = {
        message: input,
        page_context: {
          route: location.pathname,
          workspace_id: 'ws_default', // TODO: Get from auth context
          user_id: 'user_default',    // TODO: Get from auth context
          experiment_ids: [],
          protocol_ids: [],
          filters: {},
          metadata: {},
        },
        stream: false,
      };

      // Call backend API
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(chatRequest),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
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
      
      // Store agent for TTS voice selection
      lastAgentRef.current = data.agent_used;
      
      // Speak response if voice is enabled
      if (isVoiceEnabled && data.response) {
        speak(data.response, data.agent_used);
      }

    } catch (error) {
      console.error('Chat API error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `Sorry, I couldn't connect to the backend. Make sure the server is running at ${API_URL}. Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        role: 'assistant',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle mic button click - start listening
  const handleMicClick = async () => {
    if (isListening) return; // Already listening
    
    try {
      const transcript = await listen();
      if (transcript) {
        setInput(transcript);
        // Focus the input so user can edit/confirm
        inputRef.current?.focus();
      }
    } catch (error) {
      // Error already logged in useVoice hook
    }
  };

  return (
    <Card className="flex flex-col h-[280px]">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <Bot className="h-4 w-4 text-primary" />
          </div>
          <div>
            <CardTitle className="text-base">12Record Assistant</CardTitle>
            <p className="text-xs text-muted-foreground">
              {isSpeaking ? (
                <span className="text-primary animate-pulse">Speaking...</span>
              ) : (
                'Powered by SpoonOS'
              )}
            </p>
          </div>
        </div>
        
        {/* Voice toggle and stop button */}
        <div className="flex items-center gap-1">
          {isSpeaking && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={stopSpeaking}
              title="Stop speaking"
            >
              <Square className="h-3 w-3 fill-current" />
            </Button>
          )}
          {isVoiceAvailable && (
            <Button
              variant="ghost"
              size="icon"
              className={`h-7 w-7 ${isVoiceEnabled ? 'text-primary' : 'text-muted-foreground'}`}
              onClick={toggleVoice}
              title={isVoiceEnabled ? 'Disable voice' : 'Enable voice'}
            >
              {isVoiceEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col flex-1 p-4 pt-0">
        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-3 py-2 text-sm">
                  <span className="animate-pulse">Thinking...</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="mt-4 rounded-xl border border-border bg-background shadow-sm p-3">
          <input
            ref={inputRef}
            type="text"
            placeholder={isListening ? "Listening..." : "Ask anything. Type @ for mentions and / for shortcuts."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSend()}
            disabled={isLoading || isListening}
            className={`w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none mb-3 ${
              isListening ? 'placeholder:text-primary placeholder:animate-pulse' : ''
            }`}
          />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-lg bg-primary/10 text-primary hover:bg-primary/20"
              >
                <Search className="h-4 w-4" />
              </Button>
              <div className="h-4 w-px bg-border mx-1" />
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                <Globe className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                <Copy className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                <Paperclip className="h-4 w-4" />
              </Button>
              {/* Mic button - voice input */}
              <Button 
                variant="ghost" 
                size="icon" 
                className={`h-8 w-8 ${
                  isListening 
                    ? 'text-primary bg-primary/10 animate-pulse' 
                    : isSTTSupported 
                      ? 'text-muted-foreground hover:text-foreground' 
                      : 'text-muted-foreground/50 cursor-not-allowed'
                }`}
                onClick={handleMicClick}
                disabled={!isSTTSupported || isListening || isLoading}
                title={
                  !isSTTSupported 
                    ? 'Speech recognition not supported in this browser' 
                    : isListening 
                      ? 'Listening...' 
                      : 'Click to speak'
                }
              >
                {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              </Button>
              <Button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                size="icon"
                className="h-8 w-8 rounded-lg"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};