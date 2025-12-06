import { useState, useEffect } from 'react';
import { FlaskConical, BookOpen, ShoppingCart } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { DashboardCard } from '@/components/dashboard/DashboardCard';
import { QuickActions } from '@/components/dashboard/QuickActions';
import { MessageBoard } from '@/components/dashboard/MessageBoard';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';

const Dashboard = () => {
  const [experimentCount, setExperimentCount] = useState(0);
  const [protocolCount, setProtocolCount] = useState(0);
  const [orderCount, setOrderCount] = useState(0);
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      fetchCounts();
    }
  }, [user]);

  const fetchCounts = async () => {
    const [experiments, protocols, orders] = await Promise.all([
      supabase.from('experiments').select('id', { count: 'exact', head: true }),
      supabase.from('protocols').select('id', { count: 'exact', head: true }),
      supabase.from('orders').select('id', { count: 'exact', head: true }).eq('status', 'pending'),
    ]);

    setExperimentCount(experiments.count || 0);
    setProtocolCount(protocols.count || 0);
    setOrderCount(orders.count || 0);
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Welcome to your research lab workspace</p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <DashboardCard
            title="Latest Experiments"
            description="View all your experiments"
            count={experimentCount}
            icon={FlaskConical}
            href="/experiments"
          />
          <DashboardCard
            title="Protocols"
            description="Browse your protocols"
            count={protocolCount}
            icon={BookOpen}
            href="/protocols"
          />
          <DashboardCard
            title="Pending Orders"
            description="Orders awaiting approval"
            count={orderCount}
            icon={ShoppingCart}
            href="/orders"
          />
        </div>

        <div>
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          <QuickActions />
        </div>

        <MessageBoard />
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
