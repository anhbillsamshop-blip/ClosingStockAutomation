export const generateMockFiles = (count, prefix = '') => {
  const files = [];

  for (let i = 1; i <= count; i++) {
    const name = `${prefix ? `${prefix}_` : ''}data_export_${new Date().getTime() - i * 86400000}.csv`;

    files.push({
      id: `file-${i}`,
      name,
      size: `${(Math.random() * 100 + 5).toFixed(2)} MB`,
      rows: Math.floor(Math.random() * 500000 + 10000).toLocaleString(),
      columns: Math.floor(Math.random() * 50 + 5),
      status: 'pending',
      progress: 0,
      log: [],
      selected: false,
    });
  }

  return files;
};
