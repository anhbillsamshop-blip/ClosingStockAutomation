import { Terminal } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

function lineColor(message) {
  const value = message.toLowerCase();

  if (
    value.includes('error') ||
    value.includes('lỗi') ||
    value.includes('failed')
  ) {
    return 'text-red-400';
  }

  if (
    value.includes('hoàn tất') ||
    value.includes('complete') ||
    value.includes('success')
  ) {
    return 'text-emerald-400';
  }

  if (
    value.includes('warning') ||
    value.includes('dừng')
  ) {
    return 'text-amber-400';
  }

  return 'text-slate-300';
}

function highlightKeyword(message, keyword) {
  const query = keyword.trim();

  if (!query) return message;

  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  const parts = message.split(
    new RegExp(`(${escapedQuery})`, 'ig')
  );

  return parts.map((part, index) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark
        key={`${part}-${index}`}
        className="rounded bg-yellow-300 px-0.5 text-slate-950"
      >
        {part}
      </mark>
    ) : (
      part
    )
  );
}

export default function SystemLogs({ globalLog, setGlobalLog, files }) {
  const [activeLog, setActiveLog] = useState('all');
  const [keyword, setKeyword] = useState('');

  // Container chứa scrollbar
  const logContainerRef = useRef(null);

  // true = user đang ở cuối log
  // false = user đang kéo lên xem log cũ
  const isAtBottomRef = useRef(true);

  const selectedFile = files.find((file) => file.id === activeLog);

  const visibleLogs = useMemo(() => {
    const source =
      activeLog === 'all'
        ? globalLog.map((entry) => ({
            time: entry.time,
            message: entry.message,
            type: entry.type,
          }))
        : (selectedFile?.log || []).map((message) => ({
            time: '',
            message,
            type: 'info',
          }));

    const query = keyword.trim().toLowerCase();

    return query
      ? source.filter((entry) =>
          entry.message.toLowerCase().includes(query)
        )
      : source;
  }, [activeLog, globalLog, keyword, selectedFile]);

  // Theo dõi vị trí scrollbar của người dùng
  const handleLogScroll = () => {
    const container = logContainerRef.current;

    if (!container) return;

    const distanceFromBottom =
      container.scrollHeight -
      container.scrollTop -
      container.clientHeight;

    // Sai số 20px để coi như đang ở cuối
    isAtBottomRef.current = distanceFromBottom <= 20;
  };

  // Khi có log mới:
  // - Nếu đang ở cuối -> tự cuộn xuống
  // - Nếu đang xem log cũ -> giữ nguyên vị trí
  useEffect(() => {
    const container = logContainerRef.current;

    if (!container) return;

    if (isAtBottomRef.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [visibleLogs]);

  // Khi đổi tab log -> luôn đưa về cuối
  useEffect(() => {
    const container = logContainerRef.current;

    if (!container) return;

    isAtBottomRef.current = true;

    requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight;
    });
  }, [activeLog]);

  return (
    <section className="bg-slate-900 rounded-xl shadow-lg border border-slate-800 overflow-hidden flex flex-col h-64">
      <div className="bg-slate-800 px-4 py-2 border-b border-slate-700 flex items-center justify-between gap-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 whitespace-nowrap">
          <Terminal className="w-4 h-4" />
          System Console Output
        </h3>

        <div className="flex items-center gap-2">
          <input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="Filter logs..."
            className="w-40 rounded border border-slate-600 bg-slate-900 px-2 py-1 text-xs text-slate-200 outline-none focus:border-blue-400"
          />

          <button
            onClick={() => setGlobalLog([])}
            className="text-xs text-slate-400 hover:text-white whitespace-nowrap"
          >
            Clear All
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1 overflow-x-auto bg-slate-850 px-3 py-2 border-b border-slate-700">
        <button
          onClick={() => setActiveLog('all')}
          className={`px-3 py-1 rounded text-xs whitespace-nowrap ${
            activeLog === 'all'
              ? 'bg-blue-600 text-white'
              : 'text-slate-400 hover:bg-slate-700'
          }`}
        >
          All Logs
        </button>

        {files.map((file) => (
          <button
            key={file.id}
            onClick={() => setActiveLog(file.id)}
            className={`px-3 py-1 rounded text-xs whitespace-nowrap ${
              activeLog === file.id
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:bg-slate-700'
            }`}
            title={file.name}
          >
            {file.profile || file.name}
          </button>
        ))}
      </div>

      <div
        ref={logContainerRef}
        onScroll={handleLogScroll}
        className="p-4 overflow-y-auto flex-grow font-mono text-xs whitespace-pre-wrap"
      >
        {visibleLogs.length === 0 ? (
          <p className="text-slate-600 italic">
            No matching activity.
          </p>
        ) : (
          visibleLogs.map((log, index) => (
            <div
              key={`${log.time}-${index}`}
              className="mb-1 leading-relaxed"
            >
              {log.time && (
                <span className="text-slate-500 select-none">
                  [{log.time]}{' '}
                </span>
              )}

              <span
                className={
                  log.type
                    ? lineColor(log.message)
                    : 'text-slate-300'
                }
              >
                {highlightKeyword(log.message, keyword)}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}