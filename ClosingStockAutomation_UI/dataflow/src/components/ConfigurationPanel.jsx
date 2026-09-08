import {
  FolderOpen,
  Search,
  Settings,
  RefreshCw,
} from 'lucide-react';

export default function ConfigurationPanel({
  sourceDirectory,
  setSourceDirectory,
  prefixFilter,
  setPrefixFilter,
  scanDirectory,
  isScanning,
}) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
        <Settings className="w-5 h-5 text-slate-500" />
        Source Configuration
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Shared Drive Directory
          </label>

          <div className="flex rounded-md shadow-sm">
            <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-slate-300 bg-slate-50 text-slate-500">
              <FolderOpen className="w-4 h-4" />
            </span>

            <input
              type="text"
              value={sourceDirectory}
              onChange={(e) => setSourceDirectory(e.target.value)}
              className="flex-1 block w-full min-w-0 rounded-none sm:text-sm border-slate-300 px-3 py-2 border focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="e.g., Z:\\Data\\Exports"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  scanDirectory();
                }
              }}
            />

            <button
              onClick={scanDirectory}
              disabled={isScanning}
              className="px-4 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isScanning ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                'Scan'
              )}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            File Prefix Filter
          </label>

          <div className="flex rounded-md shadow-sm">
            <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-slate-300 bg-slate-50 text-slate-500">
              <Search className="w-4 h-4" />
            </span>

            <input
              type="text"
              value={prefixFilter}
              onChange={(e) => setPrefixFilter(e.target.value)}
              className="flex-1 block w-full min-w-0 rounded-none rounded-r-md sm:text-sm border-slate-300 px-3 py-2 border focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="e.g., sales_report"
            />
          </div>
        </div>
      </div>
    </section>
  );
}