import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import time
import google.generativeai as genai
import json

# 1. Configuramos la página 
st.set_page_config(page_title="Superstore Analytics", page_icon="🛒", layout="wide")
st.title("💸 Superstore Analytics - Panel Financiero con IA")
st.markdown("Sube tu reporte de ventas. Nuestro motor de Inteligencia Artificial entenderá tus columnas automáticamente y generará el panel interactivo.")
st.divider()

# --- NUEVO: FUNCIÓN CEREBRO (GEMINI BLINDADO) ---
def entender_columnas_con_ia(lista_de_columnas):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # EL TRUCO PRO: Forzamos a la API a devolver un JSON estricto
        configuracion = genai.GenerationConfig(response_mime_type="application/json")
        modelo = genai.GenerativeModel('gemini-1.5-flash', generation_config=configuracion)
        
        prompt = f"""
        Eres un analista de datos. Analiza esta lista exacta de columnas de un dataset:
        {lista_de_columnas}
        
        Debes mapear qué columna original sirve para cada métrica del dashboard. 
        Reglas estrictas de búsqueda:
        - "fecha": Busca algo como Order Date, Ship Date, Fecha, Date.
        - "valor": Busca algo como Sales, Ventas, Ingresos, Total.
        - "gastos": Busca algo como Costos, Gastos, Discount (si no hay, null).
        - "ganancia": Busca algo como Profit, Ganancia, Margen.
        - "categoria": Busca algo como Category, State, Segment, Sub-Category, Ciudad.
        - "filtro": Busca algo como Region, Country, Pais.
        
        Tu respuesta DEBE tener siempre estas 6 claves. Si no encuentras coincidencia, el valor debe ser null.
        """
        
        respuesta = modelo.generate_content(prompt)
        
        # Como forzamos el mime_type, ya no hay que limpiar texto raro con .replace()
        return json.loads(respuesta.text)
        
    except Exception as e:
        st.error(f"🚨 Error de conexión o parsing con la IA: {e}")
        return {"fecha": None, "valor": None, "gastos": None, "ganancia": None, "categoria": None, "filtro": None}

# 2. Función para cargar datos SQL (Plan de respaldo)
@st.cache_data
def cargar_datos_sql():
    try:
        conexion_sql = create_engine(st.secrets["DB_URI"])
        df = pd.read_sql("SELECT * FROM registro_ventas", con=conexion_sql)
        # Convertimos a minúsculas solo para el de SQL por comodidad
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        if 'sales' in df.columns and 'profit' in df.columns:
            df['gastos'] = df['sales'] - df['profit']
        if 'order_date' in df.columns:
            df['order_date'] = pd.to_datetime(df['order_date'])
            df['mes_año'] = df['order_date'].dt.strftime('%Y-%m')
        return df, {"fecha": "order_date", "valor": "sales", "gastos": "gastos", "ganancia": "profit", "categoria": "state", "filtro": "region"}
    except Exception as e:
        st.error("Error conectando a la base de datos principal.")
        return pd.DataFrame(), {}

# --- 3. LÓGICA DE CARGA DINÁMICA DE ARCHIVOS ---
st.subheader("📁 Análisis Asistido por IA")
uploaded_file = st.file_uploader("Sube un CSV o Excel. La Inteligencia Artificial mapeará tus datos.", type=['csv', 'xlsx'])

# Variables de estado
df_ventas = pd.DataFrame()
mapa_ia = {}

if uploaded_file is not None:
    with st.container():
        col_prog, col_status = st.columns([3, 1])
        barra_progreso = col_prog.progress(0)
        texto_estado = col_status.empty()
        
        texto_estado.text("🔍 Leyendo archivo...")
        time.sleep(0.3)
        barra_progreso.progress(20)
        
        try:
            if uploaded_file.name.endswith('.csv'):
                df_ventas = pd.read_csv(uploaded_file, encoding='latin1') 
            else:
                df_ventas = pd.read_excel(uploaded_file)
            
            texto_estado.text("🧠 Consultando IA semántica...")
            barra_progreso.progress(50)
            
            # --- AQUÍ OCURRE LA MAGIA ---
            columnas_reales = list(df_ventas.columns)
            mapa_ia = entender_columnas_con_ia(columnas_reales)
            
            # --- LÍNEA DE DEBUGGING AQUÍ MISMO ---
            st.write("🧠 Diagnóstico en vivo de la IA:", mapa_ia)
            
            texto_estado.text("⚙️ Construyendo panel inteligente...")
            barra_progreso.progress(80)
            
            # Procesamos fechas si la IA encontró una
            col_fecha = mapa_ia.get('fecha')
            if col_fecha and col_fecha in df_ventas.columns:
                df_ventas[col_fecha] = pd.to_datetime(df_ventas[col_fecha], errors='coerce')
                df_ventas['mes_año_generado'] = df_ventas[col_fecha].dt.strftime('%Y-%m')
            
            # Calculamos gastos si no existen, pero sí hay ventas y ganancias
            col_valor = mapa_ia.get('valor')
            col_ganancia = mapa_ia.get('ganancia')
            col_gastos = mapa_ia.get('gastos')
            
            if col_valor and col_ganancia and not col_gastos:
                df_ventas['gastos_calculados'] = df_ventas[col_valor] - df_ventas[col_ganancia]
                mapa_ia.update({'gastos': 'gastos_calculados'})
                
            barra_progreso.progress(100)
            texto_estado.text("✅ Panel Generado")
            
        except Exception as e:
            st.error(f"Error procesando archivo: {e}")
            st.stop()
else:
    # Si NO hay archivo, usamos SQL
    st.info("💡 Mostrando información desde PostgreSQL. Sube un archivo para activar el análisis por IA.")
    df_ventas, mapa_ia = cargar_datos_sql()

if df_ventas.empty or not mapa_ia:
    st.stop()

st.divider()


# --- 4. PANEL DE CONTROL (Adaptado por IA) ---
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

# --- 5. TARJETAS DE MÉTRICAS (Adaptadas por IA) ---
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

# --- 6. GRÁFICOS INTERACTIVOS (Adaptados por IA) ---
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
