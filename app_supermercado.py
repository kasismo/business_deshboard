import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# 1. Configuramos la página 
st.set_page_config(page_title="Superstore Analytics", page_icon="🛒", layout="wide")
st.title("💸 Superstore Analytics - Panel Financiero SQL")

# 2. Función para cargar los datos DIRECTO DESDE MySQL
@st.cache_data
def cargar_datos_sql():
    # LA MAGIA DE SEGURIDAD: Llamamos a la bóveda secreta de Streamlit
    conexion_sql = create_engine(st.secrets["DB_URI"])
    
    # Hacemos la consulta SQL para traer la tabla completa
    query = "SELECT * FROM registro_ventas"
    df = pd.read_sql(query, con=conexion_sql)
    
    # Calculamos la columna de Gastos
    df['gastos'] = df['sales'] - df['profit']
    
    # Extraemos el Año y Mes para los gráficos
    df['mes_año'] = df['order_date'].dt.strftime('%Y-%m')
    
    return df

# Ejecutamos la función
df_ventas = cargar_datos_sql()

# 3. INTERFAZ: Filtro interactivo lateral
st.sidebar.header("⚙️ Panel de Control")
lista_regiones = ["Todas las Regiones"] + list(df_ventas['region'].unique())
region_seleccionada = st.sidebar.selectbox("📍 Selecciona una Región:", lista_regiones)

# Filtramos la tabla si eligen una región
if region_seleccionada != "Todas las Regiones":
    df_ventas = df_ventas[df_ventas['region'] == region_seleccionada]

# 4. CÁLCULOS: Sumamos los totales
total_ventas = df_ventas['sales'].sum()
total_gastos = df_ventas['gastos'].sum()
total_ganancia = df_ventas['profit'].sum()

# 5. INTERFAZ: Tarjetas de Métricas
st.subheader(f"📊 Resumen de {region_seleccionada}")
col1, col2, col3 = st.columns(3)

col1.metric("💰 Ventas Totales", f"${total_ventas:,.2f}")
col2.metric("📉 Gastos Totales", f"${total_gastos:,.2f}")
col3.metric("💎 Ganancia Neta", f"${total_ganancia:,.2f}")

st.divider()

# 6. INTERFAZ: Gráficos interactivos
columna_izq, columna_der = st.columns(2)

with columna_izq:
    st.subheader("📈 Evolución Mensual")
    evolucion_mensual = df_ventas.groupby('mes_año')[['sales', 'gastos', 'profit']].sum()
    st.line_chart(evolucion_mensual)

with columna_der:
    st.subheader("🗺️ Top 10 Estados con Más Ventas")
    ventas_por_estado = df_ventas.groupby('state')['sales'].sum().sort_values(ascending=False).head(10)
    st.bar_chart(ventas_por_estado, color="#2ECC71")