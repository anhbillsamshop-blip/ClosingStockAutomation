import { useCallback, useEffect, useMemo, useState } from 'react';
import Header from './components/Header';
import ConfigurationPanel from './components/ConfigurationPanel';
import SchedulePanel from './components/SchedulePanel';
import Workspace from './components/Workspace';
import SystemLogs from './components/SystemLogs';
import useConversion from './hooks/useConversion';

// (Tuỳ chọn) Nếu bạn không dùng mock data nữa thì có thể xóa dòng import này
// import { generateMockFiles } from './data/mockFiles';

export default function App() {
  const [sourceDirectory, setSourceDirectory] = useState('C:\\SharedDrive\\DataExports\\');
  const [prefixFilter, setPrefixFilter] = useState('');
  const [globalLog, setGlobalLog] = useState([]);

  const [scheduleTime, setScheduleTime] = useState('');
  const [isScheduleActive, setIsScheduleActive] = useState(false);
  const [showSchedulePanel, setShowSchedulePanel] = useState(false);
  
  // Thêm state quản lý trạng thái scan
  const [isScanning, setIsScanning] = useState(false);

  const addLog = useCallback((message, type = 'info') => {
    const time = new Date().toLocaleTimeString();
    setGlobalLog((prev) => [...prev, { time, message, type }]);
  }, []);

  const {
    files,
    setFiles,
    isProcessing,
    startConversion,
    stopConversion,
  } = useConversion([], addLog);

  // VÔ HIỆU HÓA MOCK DATA: Bỏ comment phần này nếu bạn muốn list rỗng ban đầu, 
  // chỉ có data khi bấm Scan.
  /*
  useEffect(() => {
    setFiles(generateMockFiles(15, 'sales'));
  }, [setFiles]);
  */

  // HÀM QUÉT THƯ MỤC TỪ SERVER
  const scanDirectory = async () => {
    if (!sourceDirectory.trim()) {
      alert('Please enter a directory path.');
      return;
    }

    try {
      setIsScanning(true);
      addLog(`Scanning directory: ${sourceDirectory}...`, 'info');

      const response = await fetch('/api/files/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          directory: sourceDirectory.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Failed to scan directory');
      }

      // Đẩy dữ liệu thật từ server vào state quản lý bởi hook
      setFiles(data.files);
      addLog(`Scan complete. Found ${data.files.length} files.`, 'success');
    } catch (error) {
      console.error(error);
      alert(`Cannot scan directory:\n${error.message}`);
      addLog(`Scan error: ${error.message}`, 'error');
    } finally {
      setIsScanning(false);
    }
  };

  const filteredFiles = useMemo(() => {
    if (!prefixFilter) return files;

    return files.filter((file) =>
      file.name.toLowerCase().startsWith(prefixFilter.toLowerCase())
    );
  }, [files, prefixFilter]);

  const handleSelectAll = (e) => {
    const checked = e.target.checked;

    setFiles((prev) =>
      prev.map((file) => {
        const matchesFilter =
          !prefixFilter ||
          file.name.toLowerCase().startsWith(prefixFilter.toLowerCase());

        return matchesFilter
          ? { ...file, selected: checked }
          : file;
      })
    );
  };

  const handleSelectFile = (id) => {
    setFiles((prev) =>
      prev.map((file) =>
        file.id === id ? { ...file, selected: !file.selected } : file
      )
    );
  };

  const handleRunSelected = () => {
    const toRun = filteredFiles.filter(
      (file) =>
        file.selected &&
        file.status !== 'converting' &&
        file.status !== 'completed'
    );

    if (toRun.length === 0) {
      addLog('No valid files selected to run.', 'warning');
      return;
    }

    toRun.forEach((file) => startConversion(file.id));
  };

  const handleStopAll = () => {
    files
      .filter((file) => file.status === 'converting')
      .forEach((file) => stopConversion(file.id));

    addLog('Halted all running conversions.', 'warning');
  };

  const toggleSchedule = () => {
    if (!scheduleTime) {
      addLog('Please select a time for the schedule.', 'error');
      return;
    }

    const nextState = !isScheduleActive;
    setIsScheduleActive(nextState);

    if (nextState) {
      const selectedCount = files.filter((file) => file.selected).length;
      addLog(
        `Scheduled conversion for ${selectedCount} files at ${scheduleTime}.`,
        'info'
      );
    } else {
      addLog('Automation schedule cancelled.', 'warning');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 flex flex-col">
      <Header
        showSchedulePanel={showSchedulePanel}
        setShowSchedulePanel={setShowSchedulePanel}
        isScheduleActive={isScheduleActive}
      />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        <ConfigurationPanel
          sourceDirectory={sourceDirectory}
          setSourceDirectory={setSourceDirectory}
          prefixFilter={prefixFilter}
          setPrefixFilter={setPrefixFilter}
          // TRUYỀN HÀM VÀ STATE XUỐNG COMPONENT
          scanDirectory={scanDirectory}
          isScanning={isScanning}
        />

        {showSchedulePanel && (
          <SchedulePanel
            scheduleTime={scheduleTime}
            setScheduleTime={setScheduleTime}
            isScheduleActive={isScheduleActive}
            toggleSchedule={toggleSchedule}
          />
        )}

        <Workspace
          filteredFiles={filteredFiles}
          isProcessing={isProcessing}
          handleStopAll={handleStopAll}
          handleRunSelected={handleRunSelected}
          handleSelectAll={handleSelectAll}
          handleSelectFile={handleSelectFile}
          startConversion={startConversion}
          stopConversion={stopConversion}
        />

        <SystemLogs
          globalLog={globalLog}
          setGlobalLog={setGlobalLog}
        />
      </main>
    </div>
  );
}