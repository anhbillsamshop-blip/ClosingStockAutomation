import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
} from 'lucide-react';

export const getStatusConfig = (status) => {
  switch (status) {
    case 'completed':
      return {
        icon: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
        color: 'text-emerald-600',
        bg: 'bg-emerald-100 border border-emerald-200',
        text: 'Completed',
      };

    case 'converting':
      return {
        icon: <Activity className="w-5 h-5 text-blue-500 animate-pulse" />,
        color: 'text-blue-700',
        bg: 'bg-blue-100 border border-blue-200',
        text: 'Converting',
      };

    case 'error':
      return {
        icon: <XCircle className="w-5 h-5 text-red-500" />,
        color: 'text-red-700',
        bg: 'bg-red-100 border border-red-200',
        text: 'Failed',
      };

    case 'stopped':
      return {
        icon: <AlertCircle className="w-5 h-5 text-amber-500" />,
        color: 'text-amber-800',
        bg: 'bg-amber-100 border border-amber-200',
        text: 'Stopped',
      };

    case 'missing':
      return {
        icon: <XCircle className="w-5 h-5 text-slate-400" />,
        color: 'text-slate-500',
        bg: 'bg-slate-100 border border-slate-200',
        text: 'Not found',
      };

    default:
      return {
        icon: <Clock className="w-5 h-5 text-orange-500" />,
        color: 'text-orange-700',
        bg: 'bg-orange-100 border border-orange-200',
        text: 'Pending',
      };
  }
};