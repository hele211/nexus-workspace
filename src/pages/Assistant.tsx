import { useState, useCallback, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Send, Bot, Mic, MicOff, Volume2, VolumeX, Search, Globe, Copy, Paperclip, ArrowRight, Square } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Toggle } from '@/components/ui/toggle';
import { useVoice } from '@/hooks/useVoice';
import { useToast } from '@/hooks/use-toast';

// Backend API URL - same as AIAssistantChat
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
  conversation_id: string;
  history: Array<{ role: string; content: string }>;
  stream: boolean;
}

interface ChatResponse {
  response: string;
  agent_used: string;
  intent: string | null;
  metadata: Record<string, unknown>;
  timestamp: string;
}

const Assistant = () => {
  const { toast } = useToast();
  const location = useLocation();
  const [voiceMode, setVoiceMode] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true);
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
  const [conversationId] = useState(() => `conv_${Date.now()}`);
  const pendingResponseRef = useRef<string | null>(null);
  const lastAgentRef = useRef<string | undefined>(undefined);

  // Voice hook - same pattern as AIAssistantChat
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
      console.error('[Assistant] Voice error:', error.message);
      toast({
        title: "Voice error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Real API call to /api/chat - same as AIAssistantChat
  const handleSendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Build history from messages for context
      const history = messages
        .filter(m => m.id !== '1') // Skip initial greeting
        .map(m => ({ role: m.role, content: m.content }));

      // Build request payload - same structure as AIAssistantChat
      const chatRequest: ChatRequest = {
        message: text,
        page_context: {
          route: location.pathname,
          workspace_id: 'ws_default',
          user_id: 'user_default',
          experiment_ids: [],
          protocol_ids: [],
          filters: {},
          metadata: {},
        },
        conversation_id: conversationId,
        history: history,
        stream: false,
      };

      // Call backend API - same endpoint as AIAssistantChat
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
      
      // Store for TTS
      lastAgentRef.current = data.agent_used;
      pendingResponseRef.current = data.response;

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
  }, [messages, location.pathname, conversationId, isVoiceEnabled, speak]);

  // Speak assistant responses when voice mode is on
  useEffect(() => {
    if (voiceMode && autoSpeak && pendingResponseRef.current && !isLoading) {
      speak(pendingResponseRef.current);
      pendingResponseRef.current = null;
    }
  }, [voiceMode, autoSpeak, isLoading, speak]);

  const toggleVoiceMode = () => {
    if (!isSTTSupported) {
      toast({
        title: "Voice not supported",
        description: "Your browser doesn't support speech recognition.",
        variant: "destructive",
      });
      return;
    }
    
    if (voiceMode) {
      stopSpeaking();
      setVoiceMode(false);
    } else {
      setVoiceMode(true);
      toggleVoice();
    }
  };

  // Handle mic button click for voice input
  const handleMicClick = async () => {
    if (isListening) return;
    
    try {
      const transcript = await listen();
      if (transcript) {
        handleSendMessage(transcript);
      }
    } catch (error) {
      // Error already logged in useVoice hook
    }
  };

  const handleSend = () => {
    handleSendMessage(input);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">12Record Assistant</h1>
          <p className="text-muted-foreground mt-1">AI-powered research assistant</p>
        </div>

        <Card className="flex flex-col h-[calc(100vh-220px)] border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                <Bot className="h-5 w-5 text-foreground" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">12Record</CardTitle>
                <p className="text-xs text-primary">Powered by SpoonOS</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setAutoSpeak(!autoSpeak)}
                disabled={!voiceMode}
                className="h-9 w-9 rounded-lg"
              >
                {autoSpeak ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
              </Button>
              <Button
                variant={voiceMode ? "default" : "outline"}
                size="sm"
                onClick={toggleVoiceMode}
                className={`rounded-lg ${voiceMode && isListening ? "animate-pulse" : ""}`}
              >
                <Mic className="h-4 w-4 mr-2" />
                Voice Mode
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col flex-1 p-6 pt-4">
            <ScrollArea className="flex-1 pr-4">
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-foreground'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-xl px-4 py-3 text-sm">
                      <span className="animate-pulse">Thinking...</span>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {voiceMode ? (
              <div className="flex flex-col items-center gap-2 mt-4 py-4">
                <Button
                  size="lg"
                  variant={isListening ? "default" : "outline"}
                  className={`rounded-full h-16 w-16 ${isListening ? "animate-pulse bg-destructive hover:bg-destructive/90" : ""}`}
                  onClick={handleMicClick}
                  disabled={isSpeaking || isListening}
                >
                  {isListening ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
                </Button>
                <p className="text-sm text-muted-foreground">
                  {isSpeaking ? "Speaking..." : isListening ? "Listening..." : "Tap to speak"}
                </p>
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-border bg-background shadow-sm p-4">
                <input
                  type="text"
                  placeholder={isListening ? "Listening..." : "Ask anything. Type @ for mentions and / for shortcuts."}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                  disabled={isLoading || isListening}
                  className={`w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none mb-4 ${
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
                          ? 'Speech recognition not supported' 
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
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Assistant;
