CLOSING STOCK AUTOMATION - BO CHAY

1) Copy thu muc app/ cua ban vao cung cap voi server.py, hoac dat 4 file Python cung cap voi app_run_all.py.
2) Kiem tra app_run_all.py co dung ten 4 file Python:
   - 30D_sales.py
   - closing.stock.py
   - stock_intransit.py
   - scct.py
3) Ban React hien tai can duoc BUILD thanh dataflow\dist tren mot may co Node.js.
4) Sau khi co dataflow\dist, may chay cuoi khong can Node/npm. Chi can Python va cac package cua 4 script.
5) Chay run_app.bat.
6) Mo http://127.0.0.1:3001/

API:
POST /api/run-all  -> chay app_run_all.py
GET  /api/status   -> trang thai va log
POST /api/files/scan -> scan thu muc

Luu y: server.py khong tu y sua/xoa input. Viec xoa output/copy Network nam trong app_run_all.py.
