import subprocess
import sys
import socket
import shutil
import threading

# 1. تثبيت المكتبات المطلوبة تلقائياً إذا لم تكن موجودة
def install_packages():
    required = ['flask', 'requests']
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            print(f"[*] جاري تثبيت المكتبة: {pkg} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_packages()

from flask import Flask, Response, request
import requests

app = Flask(__name__)

# رابط البث الأساسي (المجلد الرئيسي للقناة)
BASE_STREAM_URL = "http://45.67.56.78/Sport5/"
MAIN_PLAYLIST = "index.fmp4.m3u8"

# دالة لإيجاد بورت غير مستخدم تلقائياً
def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

@app.route('/')
@app.route('/<path:subpath>')
def proxy(subpath=MAIN_PLAYLIST):
    target_url = BASE_STREAM_URL + subpath
    if request.query_string:
        target_url += "?" + request.query_string.decode('utf-8')

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # جلب البث من الشبكة المحلية
        r = requests.get(target_url, headers=headers, stream=True, timeout=10)
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        resp_headers = [
            (name, value) for (name, value) in r.raw.headers.items()
            if name.lower() not in excluded_headers
        ]
        # إضافة صلاحيات CORS ليعمل على كل المشغلات والمتصفحات
        resp_headers.append(('Access-Control-Allow-Origin', '*'))
        resp_headers.append(('Cache-Control', 'no-cache'))

        return Response(
            r.iter_content(chunk_size=16384),
            status=r.status_code,
            headers=resp_headers,
            content_type=r.headers.get('Content-Type', 'application/octet-stream')
        )
    except Exception as e:
        return Response(f"Error fetching stream: {str(e)}", status=502)

# تشغيل نفق Cloudflare لإعطاء رابط عالمي
def start_tunnel(port):
    if shutil.which("cloudflared") is None:
        print("\n[!] أداة cloudflared غير مثبتة على جهازك.")
        print("    للحصول على رابط عالمي، قم بتثبيتها عبر الأمر التالي:")
        print("    ويندوز: winget install --id Cloudflare.cloudflared")
        print("    لينكس: sudo apt install cloudflared")
        return

    print(f"\n[*] جاري إنشاء رابط عالمي للبورت {port} ...")
    subprocess.Popen(["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"])

if __name__ == '__main__':
    port = get_free_port()
    print(f"==========================================")
    print(f"[+] تم تشغيل السيرفر على البورت: {port}")
    print(f"[+] الرابط المحلي: http://127.0.0.1:{port}/{MAIN_PLAYLIST}")
    print(f"[+] لإيقاف السيرفر اضغط: Ctrl + C")
    print(f"==========================================")
    
    # تشغيل النفق في الخلفية
    threading.Thread(target=start_tunnel, args=(port,), daemon=True).start()
    
    # تشغيل سيرفر Flask
    app.run(host='0.0.0.0', port=port, threaded=True)