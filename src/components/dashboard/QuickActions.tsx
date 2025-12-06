import { useState } from 'react';
import { Plus, FlaskConical, BookOpen, ShoppingCart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { NewExperimentModal } from '@/components/modals/NewExperimentModal';
import { NewProtocolModal } from '@/components/modals/NewProtocolModal';
import { NewOrderModal } from '@/components/modals/NewOrderModal';

export const QuickActions = () => {
  const [experimentOpen, setExperimentOpen] = useState(false);
  const [protocolOpen, setProtocolOpen] = useState(false);
  const [orderOpen, setOrderOpen] = useState(false);

  return (
    <>
      <div className="flex flex-wrap gap-3">
        <Button onClick={() => setExperimentOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          <FlaskConical className="h-4 w-4 mr-2" />
          New Experiment
        </Button>
        <Button variant="outline" onClick={() => setProtocolOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          <BookOpen className="h-4 w-4 mr-2" />
          New Protocol
        </Button>
        <Button variant="outline" onClick={() => setOrderOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          <ShoppingCart className="h-4 w-4 mr-2" />
          New Order
        </Button>
      </div>

      <NewExperimentModal open={experimentOpen} onOpenChange={setExperimentOpen} />
      <NewProtocolModal open={protocolOpen} onOpenChange={setProtocolOpen} />
      <NewOrderModal open={orderOpen} onOpenChange={setOrderOpen} />
    </>
  );
};
