"""
Gmail SMTP ile rapor ve bildirim e-postası gönderir.
Gmail hesabında App Password oluşturulmuş olmalı.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from . import config_loader as cfg
from .logger import get_logger

log = get_logger("gmail")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(subject: str, body_html: str,
               recipient: str = None, body_text: str = None) -> bool:
    sender    = cfg.GMAIL_SENDER
    password  = cfg.GMAIL_APP_PASSWORD
    recipient = recipient or cfg.GMAIL_RECIPIENT

    if not password:
        log.warning("GMAIL_APP_PASSWORD tanımlı değil, e-posta atlanıyor")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient

    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        log.info("E-posta gönderildi → %s | Konu: %s", recipient, subject)
        return True
    except Exception as e:
        log.error("E-posta hatası: %s", e)
        return False


def send_daily_report(report_data: dict) -> bool:
    today = datetime.now().strftime("%d.%m.%Y")
    subject = f"Limsa Club — Günlük Özet {today}"

    shopify   = report_data.get("shopify", {})
    trendyol  = report_data.get("trendyol", {})
    stripe    = report_data.get("stripe", {})
    alerts    = report_data.get("alerts", [])
    low_stock = report_data.get("low_stock", [])

    alerts_html = "".join(f"<li style='color:#e74c3c'>{a}</li>" for a in alerts) or "<li>—</li>"
    stock_html  = "".join(
        f"<tr><td>{s['product']}</td><td>{s['variant']}</td>"
        f"<td style='color:#e74c3c;font-weight:bold'>{s['quantity']}</td></tr>"
        for s in low_stock
    ) or "<tr><td colspan='3'>Kritik stok yok ✅</td></tr>"

    html = f"""
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8">
<style>
  body {{font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:700px;margin:auto;padding:20px}}
  h1   {{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:8px}}
  h2   {{color:#2980b9;margin-top:24px}}
  .box {{background:#f8f9fa;border-left:4px solid #3498db;padding:12px 16px;margin:8px 0;border-radius:4px}}
  .ok  {{color:#27ae60;font-weight:bold}}
  .warn{{color:#e67e22;font-weight:bold}}
  table{{border-collapse:collapse;width:100%;margin:8px 0}}
  th   {{background:#3498db;color:#fff;padding:8px;text-align:left}}
  td   {{padding:7px;border-bottom:1px solid #eee}}
  .footer{{margin-top:32px;color:#888;font-size:12px;border-top:1px solid #eee;padding-top:12px}}
</style>
</head>
<body>
<h1>🏪 Limsa Club — Günlük Özet</h1>
<p><strong>Tarih:</strong> {today} | <strong>Saat:</strong> {datetime.now().strftime('%H:%M')}</p>

<h2>🛍 Shopify</h2>
<div class="box">
  <p>Bugünkü sipariş: <strong>{shopify.get('today_orders', 0)}</strong> adet</p>
  <p>Bugünkü ciro: <strong>${shopify.get('today_revenue', 0):.2f}</strong></p>
  <p>Bu ay toplam: <strong>${shopify.get('month_revenue', 0):.2f}</strong> ({shopify.get('month_orders', 0)} sipariş)</p>
  <p>Aktif ürün: <strong>{shopify.get('active_products', 0)}</strong></p>
</div>

<h2>🛒 Trendyol</h2>
<div class="box">
  <p>Yeni sipariş (son 24s): <strong>{trendyol.get('new_orders', 0)}</strong> adet</p>
  <p>Toplam bekleyen: <strong>{trendyol.get('pending_orders', 0)}</strong> adet</p>
  <p>Bekleyen ödeme: <strong>{trendyol.get('pending_payment', '—')} ₺</strong></p>
</div>

<h2>💳 Stripe</h2>
<div class="box">
  <p>Mevcut bakiye: <strong>${stripe.get('balance_usd', 0):.2f}</strong></p>
  <p>Son 7 gün ciro: <strong>${stripe.get('week_revenue', 0):.2f}</strong></p>
  <p>Son 7 gün sipariş: <strong>{stripe.get('week_orders', 0)}</strong> adet</p>
</div>

<h2>📦 Kritik Stok Uyarıları</h2>
<table>
  <tr><th>Ürün</th><th>Varyant</th><th>Stok</th></tr>
  {stock_html}
</table>

<h2>⚠️ Sistem Uyarıları</h2>
<ul>{alerts_html}</ul>

<div class="footer">
  Bu rapor Limsa Club Otomasyon Sistemi tarafından otomatik oluşturulmuştur.<br>
  <a href="https://limsa.club/admin">Shopify Admin</a> |
  <a href="https://partner.trendyol.com">Trendyol Panel</a>
</div>
</body>
</html>
"""
    return send_email(subject, html)


def send_weekly_report(report_data: dict) -> bool:
    from_date = report_data.get("from_date", "")
    to_date   = report_data.get("to_date", "")
    subject   = f"Limsa Club — Haftalık Analiz ({from_date} – {to_date})"

    rows = ""
    for platform, data in report_data.get("platforms", {}).items():
        rows += (
            f"<tr><td><strong>{platform}</strong></td>"
            f"<td>{data.get('orders',0)}</td>"
            f"<td>${data.get('revenue',0):.2f}</td>"
            f"<td>${data.get('avg_order',0):.2f}</td></tr>"
        )

    html = f"""
<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<style>
  body {{font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:700px;margin:auto;padding:20px}}
  h1   {{color:#2c3e50;border-bottom:3px solid #27ae60;padding-bottom:8px}}
  table{{border-collapse:collapse;width:100%;margin:16px 0}}
  th   {{background:#27ae60;color:#fff;padding:9px;text-align:left}}
  td   {{padding:8px;border-bottom:1px solid #eee}}
</style>
</head><body>
<h1>📈 Haftalık Satış Analizi</h1>
<p><strong>Dönem:</strong> {from_date} – {to_date}</p>
<table>
  <tr><th>Platform</th><th>Sipariş</th><th>Ciro</th><th>Ortalama</th></tr>
  {rows}
</table>
<p><strong>Toplam ciro:</strong> ${report_data.get('total_revenue', 0):.2f}</p>
<p><strong>Toplam sipariş:</strong> {report_data.get('total_orders', 0)}</p>
</body></html>
"""
    return send_email(subject, html)
