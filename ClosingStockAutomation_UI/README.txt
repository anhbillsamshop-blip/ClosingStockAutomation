CLOSING STOCK AUTOMATION

1) Cai dependency Python:
   python -m pip install -r ..\requirements.txt

2) Build giao dien:
   cd ClosingStockAutomation_UI\dataflow
   npm install
   npm run build

3) Chay server:
   python ClosingStockAutomation_UI\server.py

4) Mo:
   http://127.0.0.1:3001/

Trong giao dien:
- Shared Drive Directory: bam icon folder de chon folder chua 4 file CSV.
- Local Conversion Directory: bam icon folder de chon noi luu Parquet tam thoi.
- Sau khi convert thanh cong, Parquet duoc copy tu local len Network va xoa output cu cung loai.
- Scan Today's Files: chi tim 4 file co ngay YYYYMMDD cua ngay hien tai.
- Bang ket qua hien thi ca file thieu, ngay sua gan nhat va dung luong file.

API local:
- POST /api/files/scan: quet CSV trong thu muc
- POST /api/convert: convert cac file CSV da chon
- GET /api/status/<job_id>: xem tien trinh convert
- POST /api/run-all: chay lan luot 4 profile va copy output len Network

Logic convert dung chung nam trong app/converter_core.py.
Bon entry point trong app/ chi con cau hinh profile va goi core.

Task runner giong npm run:
   python -m pip install -e ".[tasks]"
   poe setup
   poe server

Task nhanh:
   poe server          -> chay UI local
   poe convert         -> chay ca 4 profile va publish Network
   poe frontend-build  -> build giao dien React
