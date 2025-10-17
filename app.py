import os
from io import BytesIO
import streamlit as st
import pandas as pd
import boto3
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

# --- Cargar variables de entorno ---
load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-west-1")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "awsdata")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# --- Función para leer CSV desde S3 ---
def read_csv_from_s3(bucket: str, key: str, region: str) -> pd.DataFrame:
    s3 = boto3.client("s3", region_name=region)
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    return pd.read_csv(BytesIO(body))

# --- Función para leer tabla desde MySQL ---
def read_table_from_mysql(table_name: str) -> pd.DataFrame:
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        query = f"SELECT * FROM {table_name};"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            st.error(f"La base de datos '{DB_NAME}' no existe.")
        elif err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            st.error("Usuario o contraseña incorrectos para MySQL.")
        else:
            st.error(str(err))
        return pd.DataFrame()

# --- Interfaz Streamlit ---
st.set_page_config(page_title="S3 + MySQL Viewer", layout="wide")
st.title("📊 Visualización de datos: CSV (S3) + Tabla MySQL")

tab1, tab2 = st.tabs(["🎬 Netflix CSV (S3)", "👥 Tabla Personas (MySQL o local)"])

with tab1:
    st.subheader("Head del CSV desde S3")
    bucket = "xideralaws-curso-benjamin-2"
    key = "netflix_titles.csv"
    try:
        df_csv = read_csv_from_s3(bucket, key, AWS_REGION)
        st.write(f"**Dimensiones:** {df_csv.shape}")
        st.dataframe(df_csv.head(10))
    except Exception as e:
        st.error(f"Error leyendo CSV desde S3: {e}")

with tab2:
    st.subheader(f"Tabla 'personas' en {DB_NAME}")
    df_db = read_table_from_mysql("personas")
    if not df_db.empty:
        st.dataframe(df_db)
    else:
        st.warning("No se encontró la tabla en la base de datos. Mostrando datos de ejemplo.")
        df_local = pd.DataFrame([
            [1, "Ana Torres", "ana.torres@example.com", "CDMX", 28]
        ], columns=["id", "nombre", "email", "ciudad", "edad"])
        st.dataframe(df_local)
