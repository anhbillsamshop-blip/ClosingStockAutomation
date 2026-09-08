import { CalendarClock, Clock, Square } from 'lucide-react';

export default function SchedulePanel({
  scheduleTime,
  setScheduleTime,
  isScheduleActive,
  toggleSchedule,
}) {
  return (
    <section className="bg-indigo-50 rounded-xl shadow-inner border border-indigo-100 p-6 animate-in slide-in-from-top-4 duration-200">
      <h2 className="text-lg font-semibold text-indigo-900 mb-4 flex items-center gap-2">
        <CalendarClock className="w-5 h-5 text-indigo-500" />
        Automated Run Schedule
      </h2>

      <div className="flex flex-col sm:flex-row items-end gap-4">
        <div className="w-full sm:w-auto">
          <label className="block text-sm font-medium text-indigo-700 mb-1">
            Select Time to Run Selected Files
          </label>

          <input
            type="time"
            value={scheduleTime}
            onChange={(e) => setScheduleTime(e.target.value)}
            className="block w-full rounded-md border-indigo-300 px-4 py-2 text-indigo-900 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
          />
        </div>

        <button
          onClick={toggleSchedule}
          className={`px-6 py-2 rounded-md font-medium text-white transition-all shadow-sm flex items-center gap-2 ${
            isScheduleActive
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-indigo-600 hover:bg-indigo-700'
          }`}
        >
          {isScheduleActive ? (
            <>
              <Square className="w-4 h-4" />
              Cancel Automation
            </>
          ) : (
            <>
              <Clock className="w-4 h-4" />
              Schedule Run
            </>
          )}
        </button>
      </div>

      {isScheduleActive && (
        <p className="mt-3 text-sm text-indigo-700 flex items-center gap-2 bg-indigo-100 p-2 rounded w-fit">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
          </span>
          Automation active. System will look for matching files and convert at{' '}
          <b>{scheduleTime}</b> daily.
        </p>
      )}
    </section>
  );
}
