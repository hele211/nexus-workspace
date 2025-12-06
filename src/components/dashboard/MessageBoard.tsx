import { useState, useEffect } from 'react';
import { Plus, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';

interface Message {
  id: string;
  content: string;
  author_name: string | null;
  created_at: string;
  user_id: string;
}

export const MessageBoard = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const { user } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    fetchMessages();

    const channel = supabase
      .channel('messages')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' }, () => {
        fetchMessages();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const fetchMessages = async () => {
    const { data, error } = await supabase
      .from('messages')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(5);

    if (error) {
      console.error('Error fetching messages:', error);
    } else {
      setMessages(data || []);
    }
  };

  const handleAddMessage = async () => {
    if (!newMessage.trim() || !user) return;

    setIsAdding(true);
    const { error } = await supabase.from('messages').insert({
      content: newMessage,
      user_id: user.id,
      author_name: user.email?.split('@')[0] || 'Anonymous',
    });

    setIsAdding(false);

    if (error) {
      toast({
        title: 'Error',
        description: 'Failed to add message',
        variant: 'destructive',
      });
    } else {
      setNewMessage('');
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Message Board
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Add a note for the team..."
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddMessage()}
          />
          <Button onClick={handleAddMessage} disabled={isAdding}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        <div className="space-y-3">
          {messages.length === 0 ? (
            <p className="text-center text-muted-foreground py-4">No messages yet</p>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className="p-3 rounded-lg bg-muted">
                <p className="text-sm">{msg.content}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    {msg.author_name || 'Anonymous'}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};
