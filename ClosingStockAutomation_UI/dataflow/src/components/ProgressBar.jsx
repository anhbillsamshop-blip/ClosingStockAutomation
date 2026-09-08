export default function ProgressBar({ progress, status }) {
  let barColor = 'bg-blue-500';

  if (status === 'completed') barColor = 'bg-emerald-500';
  if (status === 'error') barColor = 'bg-red-500';
  if (status === 'stopped') barColor = 'bg-amber-500';

  return (
    <div className="w-full flex items-center gap-3">
      <div className="flex-grow h-2.5 bg-slate-200 rounded-full overflow-hidden shadow-inner">
        <div
          className={`h-full ${barColor} transition-all duration-500 ease-out`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <span
        className={`text-xs font-semibold w-9 text-right ${
          progress === 100 ? 'text-emerald-600' : 'text-slate-600'
        }`}
      >
        {progress}%
      </span>
    </div>
  );
}
