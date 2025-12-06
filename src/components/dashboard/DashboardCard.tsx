import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LucideIcon } from 'lucide-react';

interface DashboardCardProps {
  title: string;
  description: string;
  count: number;
  icon: LucideIcon;
  href: string;
  accentColor?: string;
}

export const DashboardCard = ({ 
  title, 
  description, 
  count, 
  icon: Icon, 
  href,
}: DashboardCardProps) => {
  return (
    <Link to={href} className="block">
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-4 w-4 text-primary" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{count}</div>
          <CardDescription className="mt-1">{description}</CardDescription>
        </CardContent>
      </Card>
    </Link>
  );
};
