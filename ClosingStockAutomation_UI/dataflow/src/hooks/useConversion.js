import { useEffect, useState } from 'react';

export default function useConversion(initialFiles = [], addLog) {
  const [files, setFiles] = useState(initialFiles);
  const [isProcessing, setIsProcessing] = useState(false);

  const startConversion = (fileId) => {
    setFiles((prev) =>
      prev.map((file) => {
        if (
          file.id === fileId &&
          ['pending', 'stopped', 'error'].includes(file.status)
        ) {
          addLog(`Started conversion for ${file.name}`, 'info');

          return {
            ...file,
            status: 'converting',
            progress: 0,
            log: [`Started reading ${file.name}...`],
          };
        }

        return file;
      })
    );

    setIsProcessing(true);
  };

  const stopConversion = (fileId) => {
    setFiles((prev) =>
      prev.map((file) => {
        if (file.id === fileId && file.status === 'converting') {
          addLog(`Stopped conversion for ${file.name}`, 'warning');

          return {
            ...file,
            status: 'stopped',
            log: [...file.log, 'Conversion aborted by user.'],
          };
        }

        return file;
      })
    );
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setFiles((prevFiles) => {
        let anyConverting = false;

        const newFiles = prevFiles.map((file) => {
          if (file.status !== 'converting') return file;

          anyConverting = true;

          const nextProgress = Math.min(
            file.progress + Math.floor(Math.random() * 15 + 5),
            100
          );

          const newLog = [...file.log];

          if (nextProgress >= 20 && file.progress < 20) {
            newLog.push('Inferring schema...');
          }

          if (nextProgress >= 50 && file.progress < 50) {
            newLog.push('Writing Parquet chunks...');
          }

          if (nextProgress >= 80 && file.progress < 80) {
            newLog.push('Optimizing file size...');
          }

          if (nextProgress === 100) {
            addLog(`Successfully converted ${file.name} to Parquet.`, 'success');
            newLog.push('Conversion complete.');

            return {
              ...file,
              status: 'completed',
              progress: 100,
              log: newLog,
            };
          }

          if (Math.random() < 0.02 && nextProgress < 90) {
            addLog(
              `Error converting ${file.name}: Corrupt row detected.`,
              'error'
            );

            newLog.push('ERROR: Data type mismatch in column 14.');

            return {
              ...file,
              status: 'error',
              log: newLog,
            };
          }

          return {
            ...file,
            progress: nextProgress,
            log: newLog,
          };
        });

        setIsProcessing(anyConverting);
        return newFiles;
      });
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
