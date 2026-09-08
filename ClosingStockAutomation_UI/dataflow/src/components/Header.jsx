import { CalendarClock, FileText } from 'lucide-react';

export default function Header({
  showSchedulePanel,
  setShowSchedulePanel,
  isScheduleActive,
}) {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg shadow-md shadow-blue-200">
            <FileText className="w-6 h-6 text-white" />
          </div>

          <div>
            <h1 className="text-xl font-bold text-slate-900 leading-tight">DataFlow</h1>
            <p className="text-xs text-slate-500 font-medium">CSV to Parquet Engine</p>
          </div>
        </div>

        <button
          onClick={() => setShowSchedulePanel(!showSchedulePanel)}
          className={`relative flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            showSchedulePanel
              ? 'bg-indigo-100 text-indigo-700'
              : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <CalendarClock className="w-4 h-4" />
          Automation

          {isScheduleActive && (
            <span className="flex w-2 h-2 rounded-full bg-emerald-500 absolute -top-1 -right-1 animate-pulse" />
          )}
        </button>
      </div>
    </header>
  );
}
