import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FlaskConical, RefreshCw } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { NewExperimentModal } from '@/components/modals/NewExperimentModal';
import { formatDistanceToNow } from 'date-fns';

// Backend API URL - same source as ExperimentAgent tools
const API_URL = 'http://localhost:8000';

interface Experiment {
  id: string;
  title: string;
  description: string | null;
  status: string;
  created_at: string;
}

const Experiments = () => {
  const navigate = useNavigate();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch experiments from backend API (same source as ExperimentAgent tools)
  const fetchExperiments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/experiments`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      setExperiments(data.experiments || []);
    } catch (err) {
      console.error('Failed to fetch experiments:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch experiments');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500/10 text-green-600 border-green-500/20';
      case 'in_progress': return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
      case 'failed': return 'bg-red-500/10 text-red-600 border-red-500/20';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Experiments</h1>
            <p className="text-muted-foreground mt-1">Manage your lab experiments</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchExperiments} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Experiment
            </Button>
          </div>
        </div>

        {experiments.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FlaskConical className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No experiments yet</h3>
              <p className="text-muted-foreground mt-1">Create your first experiment to get started</p>
              <Button className="mt-4" onClick={() => setModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Experiment
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {experiments.map((exp) => (
              <Card 
                key={exp.id} 
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/experiments/${exp.id}`)}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{exp.title}</CardTitle>
                    <Badge variant="outline" className={getStatusColor(exp.status)}>
                      {exp.status.replace('_', ' ')}
                    </Badge>
                  </div>
                  <CardDescription>
                    {formatDistanceToNow(new Date(exp.created_at), { addSuffix: true })}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {exp.description || 'No description provided'}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <NewExperimentModal open={modalOpen} onOpenChange={setModalOpen} />
    </DashboardLayout>
  );
};

export default Experiments;
