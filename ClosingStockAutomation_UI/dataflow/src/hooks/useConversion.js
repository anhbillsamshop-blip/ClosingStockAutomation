import { useEffect, useRef, useState } from 'react';

export default function useConversion(initialFiles = [], addLog, outputDirectory, sourceDirectory) {
  const [files, setFiles] = useState(initialFiles);
  const [isProcessing, setIsProcessing] = useState(false);
  const jobs = useRef(new Map());

  const startConversion = async (fileIdOrIds) => {
    const fileIds = Array.isArray(fileIdOrIds) ? fileIdOrIds : [fileIdOrIds];
    const selectedFiles = files.filter((item) => (
      fileIds.includes(item.id) && ['pending', 'stopped', 'error'].includes(item.status)
    ));
    if (selectedFiles.length === 0) return;

    setFiles((previous) => previous.map((item) => (
      selectedFiles.some((file) => file.id === item.id)
        ? { ...item, status: 'converting', progress: 5, log: ['Đang gửi file tới converter...'] }
        : item
    )));
    setIsProcessing(true);
    addLog(`Bắt đầu convert ${selectedFiles.length} file`, 'info');

    try {
      const response = await fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: selectedFiles,
          output_folder: outputDirectory,
          source_directory: sourceDirectory,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Không thể bắt đầu convert');
      jobs.current.set(data.job_id, selectedFiles.map((file) => file.id));
    } catch (error) {
      setFiles((previous) => previous.map((item) => (
        selectedFiles.some((file) => file.id === item.id)
          ? { ...item, status: 'error', log: [...item.log, error.message] }
          : item
      )));
      addLog(`Convert lỗi: ${error.message}`, 'error');
    }
  };

  const stopConversion = (fileId) => {
    for (const [jobId, fileIds] of jobs.current) {
      if (fileIds.includes(fileId)) {
        fetch('/api/stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId }),
        }).catch(() => {});
      }
    }
    setFiles((previous) => previous.map((item) => (
      item.id === fileId && item.status === 'converting'
        ? { ...item, status: 'stopped', log: [...item.log, 'Đã dừng theo yêu cầu.'] }
        : item
    )));
    addLog('Đã gửi yêu cầu dừng convert.', 'warning');
  };

  useEffect(() => {
    const interval = setInterval(async () => {
      for (const [jobId, fileIds] of jobs.current) {
        try {
          const response = await fetch(`/api/status/${jobId}`);
          const job = await response.json();
          setFiles((previous) => previous.map((item) => {
            if (!fileIds.includes(item.id)) return item;
            const state = job.files?.[item.id];
            return state ? { ...item, ...state, log: state.log || item.log } : item;
          }));
          if (!job.running) {
            jobs.current.delete(jobId);
            if (job.result?.success) addLog('Convert hoàn tất.', 'success');
            if (job.result && !job.result.success) addLog(job.result.error, 'error');
          }
        } catch (error) {
          addLog(`Không đọc được trạng thái convert: ${error.message}`, 'error');
        }
      }
      setIsProcessing(jobs.current.size > 0);
    }, 1000);

    return () => clearInterval(interval);
  }, [addLog]);

  return {
    files,
    setFiles,
    isProcessing,
    startConversion,
    stopConversion,
  };
}
