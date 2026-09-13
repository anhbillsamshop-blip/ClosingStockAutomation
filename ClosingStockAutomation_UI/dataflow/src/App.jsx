import { useCallback, useEffect, useMemo, useState } from 'react';
import Header from './components/Header';
import ConfigurationPanel from './components/ConfigurationPanel';
import SchedulePanel from './components/SchedulePanel';
import Workspace from './components/Workspace';
import SystemLogs from './components/SystemLogs';
import useConversion from './hooks/useConversion';

export default function App() {
  const [sourceDirectory, setSourceDirectory] = useState(
    () => localStorage.getItem('csv-parquet-source-directory') || ''
  );
  const [outputDirectory, setOutputDirectory] = useState(
    () => localStorage.getItem('csv-parquet-output-directory') || 'D:\\ClosingStockAutomation\\CSVtoParquet'
  );
  const [globalLog, setGlobalLog] = useState([]);

  const [scheduleTime, setScheduleTime] = useState('');
  const [isScheduleActive, setIsScheduleActive] = useState(false);
  const [showSchedulePanel, setShowSchedulePanel] = useState(false);
  
  const [isScanning, setIsScanning] = useState(false);
  const [checkedFileId, setCheckedFileId] = useState(null);

  const addLog = useCallback((message, type = 'info') => {
    const time = new Date().toLocaleTimeString();
    setGlobalLog((prev) => [...prev, { time, message, type }]);
  }, []);

  useEffect(() => {
    if (sourceDirectory) {
      localStorage.setItem('csv-parquet-source-directory', sourceDirectory);
    }
  }, [sourceDirectory]);

  useEffect(() => {
    if (outputDirectory) {
      localStorage.setItem('csv-parquet-output-directory', outputDirectory);
    }
  }, [outputDirectory]);

  const clearSavedDirectories = () => {
    localStorage.removeItem('csv-parquet-source-directory');
    localStorage.removeItem('csv-parquet-output-directory');
    setSourceDirectory('');
    setOutputDirectory('D:\\ClosingStockAutomation\\CSVtoParquet');
    addLog('Đã xóa cấu hình thư mục đã lưu.', 'warning');
  };

  const {
    files,
    setFiles,
    isProcessing,
    startConversion,
    stopConversion,
  } = useConversion([], addLog, outputDirectory, sourceDirectory);

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

      setFiles(data.files);
      addLog(`Scan complete. Found ${data.found_count ?? data.count ?? 0} files.`, 'success');
    } catch (error) {
      console.error(error);
      alert(`Cannot scan directory:\n${error.message}`);
      addLog(`Scan error: ${error.message}`, 'error');
    } finally {
      setIsScanning(false);
    }
  };

  const chooseDirectory = async (target) => {
    try {
      const response = await fetch('/api/dialog/select-directory', { method: 'POST' });
      const data = await response.json();
      if (data.directory) target(data.directory);
    } catch (error) {
      addLog(`Không mở được File Explorer: ${error.message}`, 'error');
    }
  };

  const filteredFiles = useMemo(() => files, [files]);
  const checkedFile = files.find((file) => file.id === checkedFileId);

  const handleCheck = async (fileId) => {
    const file = files.find((item) => item.id === fileId);
    if (!file?.check || !file.output) {
      addLog(`Đang tải lại metadata cho ${file?.name || 'file'}...`, 'info');
      try {
        const response = await fetch('/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ input_file: file?.path, output_file: file?.output, profile: file?.profile }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Không thể đọc metadata');
        setFiles((previous) => previous.map((item) => item.id === fileId ? { ...item, check: data.check } : item));
      } catch (error) {
        addLog(`Không thể tải metadata: ${error.message}`, 'error');
      }
    }
    setCheckedFileId(fileId);
  };

  const handleSelectAll = (e) => {
    const checked = e.target.checked;

    setFiles((prev) =>
      prev.map((file) => {
        return file.status !== 'missing' ? { ...file, selected: checked } : file;
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

    startConversion(toRun.map((file) => file.id));
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

      <main className="flex-grow max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex flex-col gap-6">
        <ConfigurationPanel
          sourceDirectory={sourceDirectory}
          setSourceDirectory={setSourceDirectory}
          outputDirectory={outputDirectory}
          setOutputDirectory={setOutputDirectory}
          chooseDirectory={chooseDirectory}
          clearSavedDirectories={clearSavedDirectories}
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
          onCheck={handleCheck}
          checkedFile={checkedFile}
          onCloseCheck={() => setCheckedFileId(null)}
        />

        <SystemLogs
          globalLog={globalLog}
          setGlobalLog={setGlobalLog}
          files={files}
        />
      </main>
    </div>
  );
}