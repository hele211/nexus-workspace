import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Edit, Save, X, Clock, Tag, FlaskConical, FileText, Link2, RefreshCw } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { formatDistanceToNow } from 'date-fns';

const API_URL = 'http://localhost:8000';

interface Experiment {
  id: string;
  title: string;
  description: string | null;
  scientific_question: string | null;
  status: string;
  protocol_id: string | null;
  tags: string[];
  notes: string | null;
  results_summary: string | null;
  blockchain_tx_hash: string | null;
  created_at: string;
  updated_at: string;
}

const ExperimentDetail = () => {
  const { experimentId } = useParams<{ experimentId: string }>();
  const navigate = useNavigate();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [protocols, setProtocols] = useState<Array<{ id: string; name: string }>>([]);
  
  // Edit form state
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    scientific_question: '',
    status: '',
    protocol_id: '',
    notes: '',
    results_summary: '',
  });

  const fetchProtocols = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/protocols`);
      if (response.ok) {
        const data = await response.json();
        setProtocols(data.protocols || []);
      }
    } catch (err) {
      console.error('Failed to fetch protocols:', err);
    }
  }, []);

  const fetchExperiment = useCallback(async () => {
    if (!experimentId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/experiments/${experimentId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Experiment not found');
        }
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      setExperiment(data);
      setEditForm({
        title: data.title || '',
        description: data.description || '',
        scientific_question: data.scientific_question || '',
        status: data.status || 'planned',
        protocol_id: data.protocol_id || 'none',
        notes: data.notes || '',
        results_summary: data.results_summary || '',
      });
    } catch (err) {
      console.error('Failed to fetch experiment:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch experiment');
    } finally {
      setIsLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    fetchExperiment();
    fetchProtocols();
  }, [fetchExperiment, fetchProtocols]);

  const handleSave = async () => {
    if (!experimentId) return;
    
    setIsSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/experiments/${experimentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editForm.title || undefined,
          description: editForm.description || undefined,
          scientific_question: editForm.scientific_question || undefined,
          status: editForm.status || undefined,
          protocol_id: (editForm.protocol_id && editForm.protocol_id !== 'none') ? editForm.protocol_id : null,
          notes: editForm.notes || undefined,
          results_summary: editForm.results_summary || undefined,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update: ${response.status}`);
      }
      
      const updated = await response.json();
      setExperiment(updated);
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save experiment:', err);
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500/10 text-green-600 border-green-500/20';
      case 'in_progress': return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
      case 'failed': return 'bg-red-500/10 text-red-600 border-red-500/20';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    );
  }

  if (error || !experiment) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <Button variant="ghost" onClick={() => navigate('/experiments')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Experiments
          </Button>
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <h3 className="text-lg font-medium text-destructive">
                {error || 'Experiment not found'}
              </h3>
              <p className="text-muted-foreground mt-1">
                The experiment may have been deleted or doesn't exist.
              </p>
              <Button className="mt-4" onClick={() => navigate('/experiments')}>
                Go to Experiments
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/experiments')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              {isEditing ? (
                <Input
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="text-2xl font-bold h-auto py-1"
                  placeholder="Experiment title"
                />
              ) : (
                <h1 className="text-3xl font-bold tracking-tight">{experiment.title}</h1>
              )}
              <p className="text-muted-foreground mt-1">
                ID: <code className="text-xs bg-muted px-1 py-0.5 rounded">{experiment.id}</code>
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button variant="outline" onClick={() => setIsEditing(false)} disabled={isSaving}>
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={isSaving}>
                  <Save className="h-4 w-4 mr-2" />
                  {isSaving ? 'Saving...' : 'Save'}
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={fetchExperiment}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
                <Button variant="outline" onClick={() => setIsEditing(true)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
              </>
            )}
            <Badge variant="outline" className={getStatusColor(experiment.status)}>
              {experiment.status.replace('_', ' ')}
            </Badge>
          </div>
        </div>

        {/* Status (editable) */}
        {isEditing && (
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent>
              <Select
                value={editForm.status}
                onValueChange={(value) => setEditForm({ ...editForm, status: value })}
              >
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="planned">Planned</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>
        )}

        {/* Metadata */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Created
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                {formatDistanceToNow(new Date(experiment.created_at), { addSuffix: true })}
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Updated
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                {formatDistanceToNow(new Date(experiment.updated_at), { addSuffix: true })}
              </p>
            </CardContent>
          </Card>
          
        {/* Protocol */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Link2 className="h-4 w-4" />
                Protocol
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isEditing ? (
                <Select
                  value={editForm.protocol_id}
                  onValueChange={(value) => setEditForm({ ...editForm, protocol_id: value })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a protocol" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {protocols.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : experiment.protocol_id ? (
                <Button
                  variant="link"
                  className="p-0 h-auto text-sm"
                  onClick={() => navigate(`/protocols/${experiment.protocol_id}`)}
                >
                  {experiment.protocol_id}
                </Button>
              ) : (
                <p className="text-sm text-muted-foreground">No protocol linked</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Scientific Question */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4" />
              Scientific Question
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={editForm.scientific_question}
                onChange={(e) => setEditForm({ ...editForm, scientific_question: e.target.value })}
                placeholder="What question is this experiment trying to answer?"
                rows={2}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                {experiment.scientific_question || 'No scientific question defined'}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Description */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Description
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                placeholder="Describe the experiment..."
                rows={4}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                {experiment.description || 'No description provided'}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Notes */}
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
            <CardDescription>Lab notes and observations</CardDescription>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                placeholder="Add notes..."
                rows={4}
              />
            ) : (
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {experiment.notes || 'No notes yet'}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Results Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Results Summary</CardTitle>
            <CardDescription>Summary of experimental results</CardDescription>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={editForm.results_summary}
                onChange={(e) => setEditForm({ ...editForm, results_summary: e.target.value })}
                placeholder="Summarize results..."
                rows={4}
              />
            ) : (
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {experiment.results_summary || 'No results recorded yet'}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Tags */}
        {experiment.tags && experiment.tags.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Tag className="h-4 w-4" />
                Tags
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {experiment.tags.map((tag) => (
                  <Badge key={tag} variant="outline">
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Blockchain */}
        {experiment.blockchain_tx_hash && (
          <Card>
            <CardHeader>
              <CardTitle>Blockchain Provenance</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                <span className="text-muted-foreground">Transaction:</span>{' '}
                <code className="text-xs bg-muted px-1 py-0.5 rounded">
                  {experiment.blockchain_tx_hash}
                </code>
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default ExperimentDetail;
