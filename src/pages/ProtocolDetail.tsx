import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Edit, Save, X, Clock, Tag, List, RefreshCw, Plus, Trash2 } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { formatDistanceToNow } from 'date-fns';

const API_URL = 'http://localhost:8000';

interface ProtocolStep {
  index: number;
  text: string;
  reagents?: string[];
  duration_minutes?: number;
  notes?: string;
}

interface Protocol {
  id: string;
  name: string;
  description: string | null;
  tags: string[];
  steps: ProtocolStep[];
  source_type: string;
  source_reference: string | null;
  created_at: string;
  updated_at: string;
  version: number;
  metadata: Record<string, unknown>;
}

const ProtocolDetail = () => {
  const { protocolId } = useParams<{ protocolId: string }>();
  const navigate = useNavigate();
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  // Edit form state
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    steps: [] as ProtocolStep[],
    tags: [] as string[],
  });

  const fetchProtocol = useCallback(async () => {
    if (!protocolId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/protocols/${protocolId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Protocol not found');
        }
        throw new Error(`API error: ${response.status}`);
      }
      const data = await response.json();
      setProtocol(data);
      setEditForm({
        name: data.name || '',
        description: data.description || '',
        steps: data.steps || [],
        tags: data.tags || [],
      });
    } catch (err) {
      console.error('Failed to fetch protocol:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch protocol');
    } finally {
      setIsLoading(false);
    }
  }, [protocolId]);

  useEffect(() => {
    fetchProtocol();
  }, [fetchProtocol]);

  const handleSave = async () => {
    if (!protocolId) return;
    
    setIsSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/protocols/${protocolId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editForm.name || undefined,
          description: editForm.description || undefined,
          steps: editForm.steps.length > 0 ? editForm.steps : undefined,
          tags: editForm.tags.length > 0 ? editForm.tags : undefined,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update: ${response.status}`);
      }
      
      const result = await response.json();
      setProtocol(result.protocol);
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save protocol:', err);
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  const updateStep = (index: number, field: keyof ProtocolStep, value: string | number | string[]) => {
    const newSteps = [...editForm.steps];
    newSteps[index] = { ...newSteps[index], [field]: value };
    setEditForm({ ...editForm, steps: newSteps });
  };

  const addStep = () => {
    const newIndex = editForm.steps.length + 1;
    setEditForm({
      ...editForm,
      steps: [...editForm.steps, { index: newIndex, text: '' }],
    });
  };

  const removeStep = (index: number) => {
    const newSteps = editForm.steps.filter((_, i) => i !== index);
    // Re-index steps
    const reindexed = newSteps.map((step, i) => ({ ...step, index: i + 1 }));
    setEditForm({ ...editForm, steps: reindexed });
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

  if (error || !protocol) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <Button variant="ghost" onClick={() => navigate('/protocols')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Protocols
          </Button>
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <h3 className="text-lg font-medium text-destructive">
                {error || 'Protocol not found'}
              </h3>
              <p className="text-muted-foreground mt-1">
                The protocol may have been deleted or doesn't exist.
              </p>
              <Button className="mt-4" onClick={() => navigate('/protocols')}>
                Go to Protocols
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
            <Button variant="ghost" size="icon" onClick={() => navigate('/protocols')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              {isEditing ? (
                <Input
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="text-2xl font-bold h-auto py-1"
                  placeholder="Protocol name"
                />
              ) : (
                <h1 className="text-3xl font-bold tracking-tight">{protocol.name}</h1>
              )}
              <p className="text-muted-foreground mt-1">
                Protocol ID: <code className="text-xs bg-muted px-1 py-0.5 rounded">{protocol.id}</code>
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
                <Button variant="outline" onClick={fetchProtocol}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
                <Button variant="outline" onClick={() => setIsEditing(true)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
              </>
            )}
            <Badge variant="secondary" className="text-sm">
              v{protocol.version}
            </Badge>
          </div>
        </div>

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
                {formatDistanceToNow(new Date(protocol.created_at), { addSuffix: true })}
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
                {formatDistanceToNow(new Date(protocol.updated_at), { addSuffix: true })}
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <List className="h-4 w-4" />
                Steps
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{protocol.steps?.length || 0} steps</p>
            </CardContent>
          </Card>
        </div>

        {/* Description */}
        <Card>
          <CardHeader>
            <CardTitle>Description</CardTitle>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                placeholder="Protocol description..."
                rows={4}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                {protocol.description || 'No description provided'}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Tags */}
        {protocol.tags && protocol.tags.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Tag className="h-4 w-4" />
                Tags
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {protocol.tags.map((tag) => (
                  <Badge key={tag} variant="outline">
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Steps */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Protocol Steps</CardTitle>
                <CardDescription>
                  {isEditing ? 'Edit the steps below' : 'Follow these steps to complete the protocol'}
                </CardDescription>
              </div>
              {isEditing && (
                <Button variant="outline" size="sm" onClick={addStep}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Step
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <div className="space-y-4">
                {editForm.steps.map((step, idx) => (
                  <div key={idx} className="flex gap-4 p-4 border rounded-lg">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-medium">
                      {idx + 1}
                    </div>
                    <div className="flex-1 space-y-2">
                      <Textarea
                        value={step.text}
                        onChange={(e) => updateStep(idx, 'text', e.target.value)}
                        placeholder="Step description..."
                        rows={2}
                      />
                      <div className="grid grid-cols-2 gap-2">
                        <Input
                          type="number"
                          value={step.duration_minutes || ''}
                          onChange={(e) => updateStep(idx, 'duration_minutes', parseInt(e.target.value) || 0)}
                          placeholder="Duration (minutes)"
                        />
                        <Input
                          value={step.reagents?.join(', ') || ''}
                          onChange={(e) => updateStep(idx, 'reagents', e.target.value.split(',').map(r => r.trim()).filter(Boolean))}
                          placeholder="Reagents (comma-separated)"
                        />
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive"
                      onClick={() => removeStep(idx)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {editForm.steps.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No steps yet. Click "Add Step" to create one.
                  </p>
                )}
              </div>
            ) : protocol.steps && protocol.steps.length > 0 ? (
              <ol className="space-y-4">
                {protocol.steps.map((step, idx) => (
                  <li key={step.index || idx} className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-medium">
                      {step.index || idx + 1}
                    </div>
                    <div className="flex-1 pt-1">
                      <p className="text-sm">{step.text}</p>
                      {step.duration_minutes && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Duration: {step.duration_minutes} minutes
                        </p>
                      )}
                      {step.notes && (
                        <p className="text-xs text-muted-foreground mt-1 italic">
                          Note: {step.notes}
                        </p>
                      )}
                      {step.reagents && step.reagents.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {step.reagents.map((reagent) => (
                            <Badge key={reagent} variant="secondary" className="text-xs">
                              {reagent}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-muted-foreground">No steps defined</p>
            )}
          </CardContent>
        </Card>

        {/* Source */}
        {protocol.source_reference && (
          <Card>
            <CardHeader>
              <CardTitle>Source</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">
                <span className="text-muted-foreground">Type:</span> {protocol.source_type}
              </p>
              <p className="text-sm mt-1">
                <span className="text-muted-foreground">Reference:</span>{' '}
                <a 
                  href={protocol.source_reference} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  {protocol.source_reference}
                </a>
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default ProtocolDetail;
