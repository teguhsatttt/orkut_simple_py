
# OrderKuota Orkut/QRIS — Python Simple Flow

Flow mengikuti skrip Node penyedia:
- **Generate order**: GET `/api/orkut/createpayment?amount=&codeqr=`
- **Cek status**: GET `/api/orkut/cekstatus?merchant=&keyorkut=`
- Jika paid → kirim invite link VIP 5 menit, single-use.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Edit `config.json`:
- `telegram.bot_token`, `vip_chat_id`
- `provider.base_url`, `paths.create`, `paths.status`
- `provider.http_method` (default GET)
- `provider.merchant`, `provider.codeqr`
- `provider.auth.mode` = none|body|basic (isi username/password jika perlu)
- `pricing.price_per_month`, `order.window_sec`, `order.poll_interval_sec`

## Run
```bash
python bot.py
```
Perintah:
- `/start` — info
- `/order` — pilih durasi 1–12 bulan, klik Bayar → createpayment → cekstatus → kirim invite.
