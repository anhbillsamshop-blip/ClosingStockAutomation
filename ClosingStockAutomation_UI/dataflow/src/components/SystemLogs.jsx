import { Terminal } from 'lucide-react';
import { useEffect, useRef } from 'react';

export default function SystemLogs({ globalLog, setGlobalLog }) {
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [globalLog]);

  return (
    <section className="bg-slate-900 rounded-xl shadow-lg border border-slate-800 overflow-hidden flex flex-col h-64">
      <div className="bg-slate-800 px-4 py-2 border-b border-slate-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Terminal className="w-4 h-4" />
          System Console Output
        </h3>

        <button
          onClick={() => setGlobalLog([])}
          className="text-xs text-slate-400 hover:text-white transition-colors"
        >
          Clear Logs
        </button>
      </div>

      <div className="p-4 overflow-y-auto flex-grow font-mono text-xs whitespace-pre-wrap">
        {globalLog.length === 0 ? (
          <p className="text-slate-600 italic">
            No activity yet. Ready for conversion.
          </p>
        ) : (
          globalLog.map((log, idx) => {
            let colorClass = 'text-slate-300';
            if (log.type === 'error') colorClass = 'text-red-400';
            if (log.type === 'success') colorClass = 'text-emerald-400';
            if (log.type === 'warning') colorClass = 'text-amber-400';

            return (
              <div key={idx} className="mb-1 leading-relaxed">
                <span className="text-slate-500 select-none">[{log.time}]</span>{' '}
                <span className={colorClass}>{log.message}</span>
              </div>
            );
          })
        )}

        <div ref={logEndRef} />
      </div>
    </section>
  );
}
