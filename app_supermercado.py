import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import time
import google.generativeai as genai
import json
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Superstore Analytics", page_icon="🛒", layout="wide")
st.title("💸 Superstore Analytics - Panel Financiero con IA")
st.markdown("Sube tu reporte de ventas. Nuestro motor curará los datos corruptos y la Inteligencia Artificial estructurará el panel automáticamente.")
st.divider()

# --- 2. EL REPARADOR EN MEMORIA ---
def reparar_archivo_en_memoria(uploaded_file):
    """
    Lee los bytes crudos, intenta decodificar formatos conflictivos (Windows/Mac)
    y devuelve un archivo 'sano' directamente en la RAM.
    """
    bytes_data = uploaded_file.getvalue()
    
    # Si es Excel (binario), lo pasamos limpio a la RAM
    if uploaded_file.name.endswith(('.xlsx', '.xls')):
        return io.BytesIO(bytes_data)
        
    # Si es CSV (texto), curamos la codificación
    encodings_comunes = ['utf-8', 'latin1', 'windows-1252', 'iso-8859-1']
    texto_sano = None
    
    for enc in encodings_comunes:
        try:
            texto_sano = bytes_data.decode(enc)
            break 
        except UnicodeDecodeError:
            continue
            
    if not texto_sano:
        raise ValueError("El archivo está demasiado corrupto para ser reparado.")
        
    return io.StringIO(texto_sano)

# --- 3. CEREBRO IA (CON RED DE SEGURIDAD) ---
def entender_columnas_con_ia(lista_de_columnas):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Quitamos la restricción de mime_type que bloqueaba la respuesta
        modelo = genai.GenerativeModel('gemini-3-flash')
        
        prompt = f"""
        Eres un analista de datos. Analiza esta lista de columnas: {lista_de_columnas}
        Mapea qué columna original sirve para cada métrica.
        - "fecha": (día, mes, date, fecha, timestamp, order date).
        - "valor": (sales, ventas, ingresos, facturacion, total).
        - "gastos": (costos, gastos, discount, egresos).
        - "ganancia": (profit, ganancia, margen, neto).
        - "categoria": (category, state, ciudad, segmento, producto).
        - "filtro": (region, pais, continente).
        
        Responde ÚNICAMENTE con la estructura JSON. No agregues comillas markdown (```json).
        Ejemplo exacto de tu respuesta:
        {{"fecha": "Order Date", "valor": "Sales", "gastos": null, "ganancia": "Profit", "categoria": "State", "filtro": "Region"}}
        """
        
        respuesta = modelo.generate_content(prompt)
        
        # Limpiamos el texto por si la IA se pone rebelde y manda markdown
        texto_limpio = respuesta.text.replace('```json', '').replace('```', '').strip()
        
        if not texto_limpio:
            raise ValueError("La IA devolvió texto vacío.")
            
        return json.loads(texto_limpio)
        
    except Exception as e:
        # PLAN DE EMERGENCIA: Si la IA falla, no rompemos la app. 
        # Intentamos buscar las columnas clásicas de Superstore nosotros mismos.
        st.toast(f"⚠️ API de IA ocupada o fallando. Activando mapeo manual de emergencia.", icon="🛠️")
        
        # Convertimos las columnas a minúsculas temporalmente para buscar mejor
        cols_lower = [c.lower() for c in lista_de_columnas]
        
        return {
            "fecha": lista_de_columnas[cols_lower.index("order date")] if "order date" in cols_lower else None,
            "valor": lista_de_columnas[cols_lower.index("sales")] if "sales" in cols_lower else None,
            "gastos": lista_de_columnas[cols_lower.index("discount")] if "discount" in cols_lower else None,
            "ganancia": lista_de_columnas[cols_lower.index("profit")] if "profit" in cols_lower else None,
            "categoria": lista_de_columnas[cols_lower.index("state")] if "state" in cols_lower else None,
            "filtro": lista_de_columnas[cols_lower.index("region")] if "region" in cols_lower else None
        }

# --- 4. FUNCIÓN SQL (CON EL BUGFIX DE LA FECHA) ---
@st.cache_data
def cargar_datos_sql():
    try:
        conexion_sql = create_engine(st.secrets["DB_URI"])
        df = pd.read_sql("SELECT * FROM registro_ventas", con=conexion_sql)
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        if 'sales' in df.columns and 'profit' in df.columns:
            df['gastos'] = df['sales'] - df['profit']
        if 'order_date' in df.columns:
            df['order_date'] = pd.to_datetime(df['order_date'])
            df['mes_año_generado'] = df['order_date'].dt.strftime('%Y-%m')
        return df, {"fecha": "order_date", "valor": "sales", "gastos": "gastos", "ganancia": "profit", "categoria": "state", "filtro": "region"}
    except Exception as e:
        st.error("Error conectando a la base de datos principal.")
        return pd.DataFrame(), {}

# --- 5. LÓGICA DE CARGA DINÁMICA (EL PIPELINE) ---
st.subheader("📁 Carga tu Base de Datos")
uploaded_file = st.file_uploader("Formato soportado: CSV o Excel.", type=['csv', 'xlsx'])

df_ventas = pd.DataFrame()
mapa_ia = {}

if uploaded_file is not None:
    with st.container():
        col_prog, col_status = st.columns([3, 1])
        barra_progreso = col_prog.progress(0)
        texto_estado = col_status.empty()
        
        try:
            # ETAPA 1: EL REPARADOR
            texto_estado.text("⚕️ Reparando estructura...")
            time.sleep(0.3)
            archivo_curado = reparar_archivo_en_memoria(uploaded_file)
            barra_progreso.progress(25)
            
            # ETAPA 2: DATA EXTRACCIÓN
            texto_estado.text("📊 Construyendo Dataframe...")
            if uploaded_file.name.endswith('.csv'):
                df_ventas = pd.read_csv(archivo_curado) 
            else:
                df_ventas = pd.read_excel(archivo_curado)
            barra_progreso.progress(50)
            
            # ETAPA 3: LA IA 
            texto_estado.text("🧠 Consultando semántica...")
            columnas_reales = list(df_ventas.columns)
            mapa_ia = entender_columnas_con_ia(columnas_reales)
            
            # ETAPA 4: MOTOR GRÁFICO
            texto_estado.text("⚙️ Ensamblando panel...")
            barra_progreso.progress(80)
            
            col_fecha = mapa_ia.get('fecha')
            if col_fecha and col_fecha in df_ventas.columns:
                df_ventas[col_fecha] = pd.to_datetime(df_ventas[col_fecha], errors='coerce')
                df_ventas['mes_año_generado'] = df_ventas[col_fecha].dt.strftime('%Y-%m')
            
            col_valor = mapa_ia.get('valor')
            col_ganancia = mapa_ia.get('ganancia')
            col_gastos = mapa_ia.get('gastos')
            
            if col_valor and col_ganancia and not col_gastos:
                df_ventas['gastos_calculados'] = df_ventas[col_valor] - df_ventas[col_ganancia]
                mapa_ia.update({'gastos': 'gastos_calculados'})
                
            barra_progreso.progress(100)
            texto_estado.text("✅ Pipeline Ejecutado")
            
        except Exception as e:
            barra_progreso.empty()
            texto_estado.empty()
            st.error(f"❌ Error crítico en el archivo: {e}")
            st.stop()
else:
    st.info("💡 Mostrando información desde PostgreSQL.")
    df_ventas, mapa_ia = cargar_datos_sql()

if df_ventas.empty or not mapa_ia:
    st.stop()

st.divider()

# --- 6. PANEL DE CONTROL (Adaptable) ---
st.sidebar.header("⚙️ Filtros Inteligentes")

region_seleccionada = "Datos Globales"
col_filtro = mapa_ia.get('filtro')

if col_filtro and col_filtro in df_ventas.columns:
    lista_regiones = ["Todos"] + list(df_ventas[col_filtro].dropna().unique())
    region_seleccionada = st.sidebar.selectbox(f"📍 Filtrar por {col_filtro}:", lista_regiones)

    if region_seleccionada != "Todos":
        df_ventas = df_ventas[df_ventas[col_filtro] == region_seleccionada]
else:
    st.sidebar.info("La IA no detectó categorías macro para filtrar.")

# --- 7. TARJETAS DE MÉTRICAS (Adaptables) ---
st.subheader(f"📊 Resumen: {region_seleccionada}")

metricas = []
col_valor = mapa_ia.get('valor')
col_gastos = mapa_ia.get('gastos')
col_ganancia = mapa_ia.get('ganancia')

if col_valor and col_valor in df_ventas.columns:
    metricas.append(("💰 Ingresos Totales", df_ventas[col_valor].sum()))
if col_gastos and col_gastos in df_ventas.columns:
    metricas.append(("📉 Costos Operativos", df_ventas[col_gastos].sum()))
if col_ganancia and col_ganancia in df_ventas.columns:
    metricas.append(("💎 Beneficio Neto", df_ventas[col_ganancia].sum()))

if metricas:
    cols = st.columns(len(metricas))
    for i, (titulo, valor) in enumerate(metricas):
        cols[i].metric(titulo, f"${valor:,.2f}")
else:
    st.warning("⚠️ La IA no detectó columnas de dinero para calcular métricas.")

st.divider()

# --- 8. GRÁFICOS INTERACTIVOS (Adaptables) ---
columna_izq, columna_der = st.columns(2)

with columna_izq:
    st.subheader("📈 Evolución Temporal")
    col_fecha = mapa_ia.get('fecha')
    
    if col_fecha and 'mes_año_generado' in df_ventas.columns and col_valor:
        columnas_grafico = [col_valor]
        if col_gastos: columnas_grafico.append(col_gastos)
        if col_ganancia: columnas_grafico.append(col_ganancia)
        
        evolucion = df_ventas.groupby('mes_año_generado')[columnas_grafico].sum()
        st.line_chart(evolucion)
    else:
        st.info("ℹ️ Gráfico no disponible: La IA no encontró columnas de fecha y valor.")

with columna_der:
    col_cat = mapa_ia.get('categoria')
    st.subheader(f"🗺️ Desglose por {col_cat if col_cat else 'Categoría'}")
    
    if col_cat and col_cat in df_ventas.columns and col_valor:
        ventas_agrupadas = df_ventas.groupby(col_cat)[col_valor].sum().sort_values(ascending=False).head(10)
        st.bar_chart(ventas_agrupadas, color="#2ECC71")
    else:
        st.info("ℹ️ Gráfico no disponible: La IA no encontró una categoría para agrupar.")
