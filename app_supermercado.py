import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import time 

# 1. Configuramos la página 
st.set_page_config(page_title="Superstore Analytics", page_icon="🛒", layout="wide")
st.title("💸 Superstore Analytics - Panel Financiero")
st.markdown("Analiza la base de datos centralizada en la nube, o sube tu propio reporte para generar un panel interactivo al instante.")
st.divider()

# 2. Función para cargar los datos DIRECTO DESDE MySQL (El Plan de Respaldo)
@st.cache_data
def cargar_datos_sql():
    try:
        conexion_sql = create_engine(st.secrets["DB_URI"])
        query = "SELECT * FROM registro_ventas"
        df = pd.read_sql(query, con=conexion_sql)
        # Estandarizamos columnas por precaución
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        if 'sales' in df.columns and 'profit' in df.columns:
            df['gastos'] = df['sales'] - df['profit']
        if 'order_date' in df.columns:
            df['order_date'] = pd.to_datetime(df['order_date'])
            df['mes_año'] = df['order_date'].dt.strftime('%Y-%m')
        return df
    except Exception as e:
        st.error(f"Error conectando a la base de datos principal: {e}")
        return pd.DataFrame()

# --- 3. LÓGICA DE CARGA DINÁMICA DE ARCHIVOS ---
st.subheader("📁 Modo Dinámico (Opcional)")
uploaded_file = st.file_uploader("Sube un nuevo dataset (CSV o Excel). El dashboard se adaptará automáticamente a los datos disponibles.", type=['csv', 'xlsx'])

if uploaded_file is not None:
    with st.container():
        col_prog, col_status = st.columns([3, 1])
        barra_progreso = col_prog.progress(0)
        texto_estado = col_status.empty()
        
        texto_estado.text("🔍 Leyendo estructura del archivo...")
        time.sleep(0.5)
        barra_progreso.progress(30)
        
        try:
            if uploaded_file.name.endswith('.csv'):
                # Añadimos encoding por si el CSV viene de un Windows en español
                df_ventas = pd.read_csv(uploaded_file, encoding='latin1') 
            else:
                df_ventas = pd.read_excel(uploaded_file)
            
            # --- MAGIA LIMPIADORA: Normalizamos columnas ---
            # Convierte 'Order Date' a 'order_date', 'SALES' a 'sales', etc.
            df_ventas.columns = df_ventas.columns.str.lower().str.replace(' ', '_')
            
            texto_estado.text("⚙️ Evaluando datos y adaptando gráficos...")
            time.sleep(0.6)
            barra_progreso.progress(70)
            
            # Intentamos calcular métricas derivadas solo si existen sus bases
            if 'sales' in df_ventas.columns and 'profit' in df_ventas.columns:
                df_ventas['gastos'] = df_ventas['sales'] - df_ventas['profit']
            
            if 'order_date' in df_ventas.columns:
                df_ventas['order_date'] = pd.to_datetime(df_ventas['order_date'], errors='coerce')
                df_ventas['mes_año'] = df_ventas['order_date'].dt.strftime('%Y-%m')
            
            barra_progreso.progress(100)
            texto_estado.text("✅ Panel Generado Exitosamente")
            st.success("Visualizando datos del archivo temporal. La conexión a la base de datos SQL está en pausa.")
            
        except Exception as e:
            barra_progreso.empty()
            texto_estado.empty()
            st.error(f"❌ Ocurrió un error al procesar tu archivo. Detalles: {e}")
            st.stop()
else:
    # --- Si NO hay archivo, usamos SQL silenciosamente ---
    st.info("💡 Mostrando información en vivo desde PostgreSQL. Sube un archivo arriba para iniciar el Modo Dinámico.")
    df_ventas = cargar_datos_sql()

# Si no hay datos (por error de SQL y no hay archivo), detenemos todo
if df_ventas.empty:
    st.stop()

st.divider()

# --- 4. PANEL DE CONTROL (ADAPTABLE) ---
st.sidebar.header("⚙️ Panel de Control")

region_seleccionada = "Datos Globales"
if 'region' in df_ventas.columns:
    lista_regiones = ["Todas las Regiones"] + list(df_ventas['region'].dropna().unique())
    region_seleccionada = st.sidebar.selectbox("📍 Selecciona una Región:", lista_regiones)

    if region_seleccionada != "Todas las Regiones":
        df_ventas = df_ventas[df_ventas['region'] == region_seleccionada]
else:
    st.sidebar.info("📌 El dataset no contiene la columna 'region' para filtrar.")

# --- 5. TARJETAS DE MÉTRICAS (ADAPTABLES) ---
st.subheader(f"📊 Resumen de {region_seleccionada}")

# Creamos una lista dinámica para poner solo las tarjetas que el archivo permite
metricas = []
if 'sales' in df_ventas.columns:
    metricas.append(("💰 Ventas Totales", df_ventas['sales'].sum()))
if 'gastos' in df_ventas.columns:
    metricas.append(("📉 Gastos Totales", df_ventas['gastos'].sum()))
if 'profit' in df_ventas.columns:
    metricas.append(("💎 Ganancia Neta", df_ventas['profit'].sum()))

if metricas:
    cols = st.columns(len(metricas))
    for i, (titulo, valor) in enumerate(metricas):
        cols[i].metric(titulo, f"${valor:,.2f}")
else:
    st.warning("⚠️ No se detectaron columnas de Ventas ('sales') o Ganancias ('profit') en este archivo.")

st.divider()

# --- 6. GRÁFICOS INTERACTIVOS (ADAPTABLES) ---
columna_izq, columna_der = st.columns(2)

with columna_izq:
    st.subheader("📈 Evolución Temporal")
    if 'mes_año' in df_ventas.columns and 'sales' in df_ventas.columns:
        # Mostramos gastos y profit en el gráfico solo si existen
        columnas_grafico = ['sales']
        if 'gastos' in df_ventas.columns: columnas_grafico.append('gastos')
        if 'profit' in df_ventas.columns: columnas_grafico.append('profit')
        
        evolucion_mensual = df_ventas.groupby('mes_año')[columnas_grafico].sum()
        st.line_chart(evolucion_mensual)
    else:
        st.info("ℹ️ Gráfico no disponible: El archivo no contiene una columna de Fechas ('order_date').")

with columna_der:
    st.subheader("🗺️ Ventas por Segmento/Estado")
    # Si no hay 'state', intentamos ver si al menos hay 'segment' o 'category' para graficar algo
    columna_agrupar = None
    for col in ['state', 'category', 'segment']:
        if col in df_ventas.columns:
            columna_agrupar = col
            break
            
    if columna_agrupar and 'sales' in df_ventas.columns:
        ventas_agrupadas = df_ventas.groupby(columna_agrupar)['sales'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(ventas_agrupadas, color="#2ECC71")
    else:
        st.info("ℹ️ Gráfico no disponible: Faltan columnas geográficas o categóricas.")
