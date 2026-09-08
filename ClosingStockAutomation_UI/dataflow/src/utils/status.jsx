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
        bg: 'bg-emerald-100',
        text: 'Completed',
      };

    case 'converting':
      return {
        icon: <Activity className="w-5 h-5 text-blue-500 animate-pulse" />,
        color: 'text-blue-600',
        bg: 'bg-blue-100',
        text: 'Converting',
      };

    case 'error':
      return {
        icon: <XCircle className="w-5 h-5 text-red-500" />,
        color: 'text-red-600',
        bg: 'bg-red-100',
        text: 'Failed',
      };

    case 'stopped':
      return {
        icon: <AlertCircle className="w-5 h-5 text-amber-500" />,
        color: 'text-amber-600',
        bg: 'bg-amber-100',
        text: 'Stopped',
      };

    default:
      return {
        icon: <Clock className="w-5 h-5 text-slate-400" />,
        color: 'text-slate-600',
        bg: 'bg-slate-100',
        text: 'Pending',
      };
  }
};