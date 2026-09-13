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
   poe package         -> tao release/ClosingStockAutomation.exe

Dong goi cho may khac (Windows):
   1. Chay package.bat tren may phat trien. Lenh nay build frontend va backend vao mot file .exe.
   2. Gui file release/ClosingStockAutomation.exe sang may dich.
   3. May dich chi can mo file .exe, khong can cai Node.js, Python hay package nao.

Khi code thay doi, chi can chay lai package.bat (hoac poe package) de tao ban .exe moi.
May build can co Node.js va moi truong Python .venv; may dich khong can hai thu nay.

Chay cho may khac trong cung LAN:
   1. Chay server tren may host bang: poe server
   2. Lay IPv4 cua may host bang lenh: ipconfig
   3. May khac mo: http://<IPv4-MAY-HOST>:3001/
   4. Neu khong truy cap duoc, mo TCP port 3001 tren Windows Firewall.
