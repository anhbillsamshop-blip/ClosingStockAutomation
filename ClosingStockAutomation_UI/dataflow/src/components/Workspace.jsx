import { Play, Square } from 'lucide-react';
import FileTable from './FileTable';

export default function Workspace({
  filteredFiles,
  isProcessing,
  handleStopAll,
  handleRunSelected,
  handleSelectAll,
  handleSelectFile,
  startConversion,
  stopConversion,
}) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <span className="font-semibold text-slate-900">{filteredFiles.length}</span>
          files found.
          <span className="font-semibold text-blue-600 ml-2">
            {filteredFiles.filter((file) => file.selected).length}
          </span>
          selected.
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={handleStopAll}
            disabled={!isProcessing}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium shadow-sm"
          >
            <Square className="w-4 h-4" />
            Stop All
          </button>

          <button
            onClick={handleRunSelected}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm shadow-blue-200 text-sm font-medium"
          >
            <Play className="w-4 h-4" />
            Run Selected
          </button>
        </div>
      </div>

      <FileTable
        filteredFiles={filteredFiles}
        handleSelectAll={handleSelectAll}
        handleSelectFile={handleSelectFile}
        startConversion={startConversion}
        stopConversion={stopConversion}
      />
    </section>
  );
}
