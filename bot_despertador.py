import requests
from datetime import datetime

# REEMPLAZA ESTO con el enlace real de tu aplicación en Streamlit
url_app = "https://businessdeshboard-k4evw29yrgwbtybueaygjm.streamlit.app"

print(f"🤖 Iniciando protocolo de despertar a las {datetime.now()}...")

try:
    # Hacemos una petición (como si alguien abriera el navegador)
    respuesta = requests.get(url_app)
    
    if respuesta.status_code == 200:
        print("✅ ¡Ping exitoso! El servidor y la base de datos están despiertos.")
    else:
        print(f"⚠️ El servidor respondió, pero con código: {respuesta.status_code}")
        
except Exception as e:
    print(f"❌ Error al intentar despertar al servidor: {e}")
