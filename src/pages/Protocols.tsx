import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, BookOpen, RefreshCw } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { NewProtocolModal } from '@/components/modals/NewProtocolModal';
import { formatDistanceToNow } from 'date-fns';

// Backend API URL - same source as ProtocolAgent tools
const API_URL = 'http://localhost:8000';

interface Protocol {
  id: string;
  name: string;  // Backend uses 'name' not 'title'
  description: string | null;
  tags: string[];
  steps: Array<{ index: number; text: string }>;
  created_at: string;
  updated_at: string;
  version: number;
}

const Protocols = () => {
  const navigate = useNavigate();
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch protocols from backend API (same source as ProtocolAgent tools)
  const fetchProtocols = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/protocols`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      setProtocols(data.protocols || []);
    } catch (err) {
      console.error('Failed to fetch protocols:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch protocols');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProtocols();
  }, [fetchProtocols]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Protocols</h1>
            <p className="text-muted-foreground mt-1">
              Manage your lab protocols
              {error && <span className="text-destructive ml-2">({error})</span>}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchProtocols} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Protocol
            </Button>
          </div>
        </div>

        {protocols.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No protocols yet</h3>
              <p className="text-muted-foreground mt-1">
                Create your first protocol via AI chat or the button above
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Try: "Create a protocol for identifying fish species using PCR"
              </p>
              <Button className="mt-4" onClick={() => setModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Protocol
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {protocols.map((protocol) => (
              <Card 
                key={protocol.id} 
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/protocols/${protocol.id}`)}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{protocol.name}</CardTitle>
                    <Badge variant="secondary">
                      v{protocol.version}
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
                  {protocol.tags && protocol.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {protocol.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {protocol.steps && protocol.steps.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-2">
                      {protocol.steps.length} steps
                    </p>
                  )}
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
