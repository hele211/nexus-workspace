import { useState, useCallback, useEffect, useRef } from 'react';
import { Send, Bot, Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Toggle } from '@/components/ui/toggle';
import { useVoice } from '@/hooks/useVoice';
import { useToast } from '@/hooks/use-toast';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

const Assistant = () => {
  const { toast } = useToast();
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
  const pendingResponseRef = useRef<string | null>(null);

  const handleSendMessage = useCallback((text: string) => {
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

    // Placeholder response - will be replaced with SpoonOS integration
    setTimeout(() => {
      const responseText = "I'm currently in demo mode. Once connected to SpoonOS, I'll be able to help you with experiments, protocols, and research queries.";
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: responseText,
        role: 'assistant',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
      pendingResponseRef.current = responseText;
    }, 1000);
  }, []);

  const handleTranscript = useCallback((text: string) => {
    handleSendMessage(text);
  }, [handleSendMessage]);

  const handleSpeakEnd = useCallback(() => {
    if (voiceMode) {
      startListening();
    }
  }, []);

  const { 
    isListening, 
    isSpeaking, 
    isSupported, 
    startListening, 
    stopListening, 
    speak, 
    stopSpeaking 
  } = useVoice({
    onTranscript: handleTranscript,
    onSpeakEnd: handleSpeakEnd,
  });

  // Speak assistant responses when voice mode is on
  useEffect(() => {
    if (voiceMode && autoSpeak && pendingResponseRef.current && !isLoading) {
      speak(pendingResponseRef.current);
      pendingResponseRef.current = null;
    }
  }, [voiceMode, autoSpeak, isLoading, speak]);

  const toggleVoiceMode = () => {
    if (!isSupported) {
      toast({
        title: "Voice not supported",
        description: "Your browser doesn't support speech recognition.",
        variant: "destructive",
      });
      return;
    }
    
    if (voiceMode) {
      stopListening();
      stopSpeaking();
      setVoiceMode(false);
    } else {
      setVoiceMode(true);
      startListening();
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

        <Card className="flex flex-col h-[calc(100vh-220px)]">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div>
                <CardTitle className="text-base">12Record</CardTitle>
                <p className="text-xs text-muted-foreground">Powered by SpoonOS</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Toggle
                pressed={autoSpeak}
                onPressedChange={setAutoSpeak}
                aria-label="Toggle auto-speak"
                disabled={!voiceMode}
                className="data-[state=on]:bg-primary/10"
              >
                {autoSpeak ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
              </Toggle>
              <Button
                variant={voiceMode ? "default" : "outline"}
                size="sm"
                onClick={toggleVoiceMode}
                className={voiceMode && isListening ? "animate-pulse" : ""}
              >
                {voiceMode ? (
                  <>
                    <MicOff className="h-4 w-4 mr-1" />
                    Exit Voice
                  </>
                ) : (
                  <>
                    <Mic className="h-4 w-4 mr-1" />
                    Voice Mode
                  </>
                )}
              </Button>
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

            {voiceMode ? (
              <div className="flex flex-col items-center gap-2 mt-4 py-4">
                <Button
                  size="lg"
                  variant={isListening ? "default" : "outline"}
                  className={`rounded-full h-16 w-16 ${isListening ? "animate-pulse bg-destructive hover:bg-destructive/90" : ""}`}
                  onClick={isListening ? stopListening : startListening}
                  disabled={isSpeaking}
                >
                  {isListening ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
                </Button>
                <p className="text-sm text-muted-foreground">
                  {isSpeaking ? "Speaking..." : isListening ? "Listening..." : "Tap to speak"}
                </p>
              </div>
            ) : (
              <div className="flex gap-2 mt-4">
                <Input
                  placeholder="Ask 12Record..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                  disabled={isLoading}
                />
                <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Assistant;
