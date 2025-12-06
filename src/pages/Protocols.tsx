import { useState, useEffect } from 'react';
import { Plus, BookOpen } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { NewProtocolModal } from '@/components/modals/NewProtocolModal';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { formatDistanceToNow } from 'date-fns';

interface Protocol {
  id: string;
  title: string;
  description: string | null;
  usage_count: number;
  created_at: string;
}

const Protocols = () => {
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    if (user) fetchProtocols();
  }, [user]);

  const fetchProtocols = async () => {
    const { data, error } = await supabase
      .from('protocols')
      .select('*')
      .order('usage_count', { ascending: false });

    if (!error && data) setProtocols(data);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Protocols</h1>
            <p className="text-muted-foreground mt-1">Manage your lab protocols</p>
          </div>
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Protocol
          </Button>
        </div>

        {protocols.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No protocols yet</h3>
              <p className="text-muted-foreground mt-1">Create your first protocol to get started</p>
              <Button className="mt-4" onClick={() => setModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Protocol
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {protocols.map((protocol) => (
              <Card key={protocol.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{protocol.title}</CardTitle>
                    <Badge variant="secondary">
                      {protocol.usage_count} uses
                    </Badge>
                  </div>
                  <CardDescription>
                    {formatDistanceToNow(new Date(protocol.created_at), { addSuffix: true })}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {protocol.description || 'No description provided'}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <NewProtocolModal open={modalOpen} onOpenChange={setModalOpen} />
    </DashboardLayout>
  );
};

export default Protocols;
