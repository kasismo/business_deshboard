import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import time # Importante para la barra de carga

# 1. Configuramos la página 
st.set_page_config(page_title="Superstore Analytics", page_icon="🛒", layout="wide")
st.title("💸 Superstore Analytics - Panel Financiero SQL")
st.markdown("Analiza la base de datos centralizada en la nube, o sube tu propio reporte de ventas para generar un panel interactivo al instante.")
st.divider()

# 2. Función para cargar los datos DIRECTO DESDE MySQL (El Plan de Respaldo)
@st.cache_data
def cargar_datos_sql():
    try:
        conexion_sql = create_engine(st.secrets["DB_URI"])
        query = "SELECT * FROM registro_ventas"
        df = pd.read_sql(query, con=conexion_sql)
        df['gastos'] = df['sales'] - df['profit']
        df['order_date'] = pd.to_datetime(df['order_date']) # Aseguramos formato de fecha
        df['mes_año'] = df['order_date'].dt.strftime('%Y-%m')
        return df
    except Exception as e:
        st.error(f"Error conectando a la base de datos principal: {e}")
        return pd.DataFrame()

# --- 3. NUEVO: LÓGICA DE CARGA DINÁMICA DE ARCHIVOS ---
st.subheader("📁 Modo Dinámico (Opcional)")
uploaded_file = st.file_uploader("Sube un nuevo dataset de ventas (CSV o Excel) para sobrescribir la vista en tiempo real.", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # --- Si suben un archivo, inicia la operación interactiva ---
    with st.container():
        col_prog, col_status = st.columns([3, 1])
        barra_progreso = col_prog.progress(0)
        texto_estado = col_status.empty()
        
        texto_estado.text("🔍 Leyendo estructura del archivo...")
        time.sleep(0.5) # Efecto visual de análisis
        barra_progreso.progress(30)
        
        try:
            if uploaded_file.name.endswith('.csv'):
                df_ventas = pd.read_csv(uploaded_file)
            else:
                df_ventas = pd.read_excel(uploaded_file)
                
            texto_estado.text("⚙️ Calculando métricas y estandarizando fechas...")
            time.sleep(0.6)
            barra_progreso.progress(70)
            
            # Recalculamos las columnas que el dashboard necesita para funcionar
            df_ventas['gastos'] = df_ventas['sales'] - df_ventas['profit']
            df_ventas['order_date'] = pd.to_datetime(df_ventas['order_date'])
            df_ventas['mes_año'] = df_ventas['order_date'].dt.strftime('%Y-%m')
            
            barra_progreso.progress(100)
            texto_estado.text("✅ Panel Generado Exitosamente")
            st.success("Visualizando datos del archivo temporal. La conexión SQL está en pausa.")
            
        except Exception as e:
            barra_progreso.empty()
            texto_estado.empty()
            st.error("❌ El archivo subido no tiene el formato correcto. Asegúrate de que contenga las columnas: 'sales', 'profit', 'order_date', 'region', y 'state'.")
            st.stop() # Detenemos la ejecución si el archivo es incompatible
else:
    # --- Si NO hay archivo, usamos SQL silenciosamente ---
    st.info("💡 Mostrando información en vivo desde la base de datos PostgreSQL. Sube un archivo para analizar datos propios.")
    df_ventas = cargar_datos_sql()

# Verificación de seguridad por si la DB está vacía o hubo error
if df_ventas.empty:
    st.stop()

st.divider()

# 4. INTERFAZ: Filtro interactivo lateral
st.sidebar.header("⚙️ Panel de Control")

# Pequeña validación por si el archivo subido no tiene columna 'region'
if 'region' in df_ventas.columns:
    lista_regiones = ["Todas las Regiones"] + list(df_ventas['region'].dropna().unique())
    region_seleccionada = st.sidebar.selectbox("📍 Selecciona una Región:", lista_regiones)

    if region_seleccionada != "Todas las Regiones":
        df_ventas = df_ventas[df_ventas['region'] == region_seleccionada]
else:
    st.sidebar.warning("El dataset subido no contiene la categoría 'region'.")
    region_seleccionada = "Datos Globales"

# 5. CÁLCULOS: Sumamos los totales
total_ventas = df_ventas['sales'].sum()
total_gastos = df_ventas['gastos'].sum()
total_ganancia = df_ventas['profit'].sum()

# 6. INTERFAZ: Tarjetas de Métricas
st.subheader(f"📊 Resumen de {region_seleccionada}")
col1, col2, col3 = st.columns(3)

col1.metric("💰 Ventas Totales", f"${total_ventas:,.2f}")
col2.metric("📉 Gastos Totales", f"${total_gastos:,.2f}")
col3.metric("💎 Ganancia Neta", f"${total_ganancia:,.2f}")

st.divider()

# 7. INTERFAZ: Gráficos interactivos
columna_izq, columna_der = st.columns(2)

with columna_izq:
    st.subheader("📈 Evolución Mensual")
    if 'mes_año' in df_ventas.columns:
        evolucion_mensual = df_ventas.groupby('mes_año')[['sales', 'gastos', 'profit']].sum()
        st.line_chart(evolucion_mensual)
    else:
        st.warning("Faltan fechas para este gráfico.")

with columna_der:
    st.subheader("🗺️ Top 10 Estados con Más Ventas")
    if 'state' in df_ventas.columns:
        ventas_por_estado = df_ventas.groupby('state')['sales'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(ventas_por_estado, color="#2ECC71")
    else:
        st.warning("Falta columna 'state' para este gráfico.")
