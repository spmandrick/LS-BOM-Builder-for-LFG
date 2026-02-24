import math
import streamlit as st
import pandas as pd
import openpyxl

LFG = "data/LFG-Logo-App_Colors.jpg"
st.title("Siemens BOM Scubber")

dirty_BOM = st.file_uploader("Select Siemens BOM to be Scrubbed", type = "xlsx")
if dirty_BOM is not None:
    df = pd.read_csv(dirty_BOM)

    df = df[["Catalog", "Description", "Designation", "Qty", "Sell Price"]]
    df["Board"] = df["Designation"].str.strip().str.split().str[0]    # Board designation
    df["Designation"] = df["Designation"].str.strip().str.split(n=1).str[1]     # Stripping board designation from designation
    df = df.groupby(['Board', 'Catalog', 'Sell Price'], as_index=False).sum(numeric_only=True)

    st.write(df)

    st.download_button(label="**Download CSV**", data = df.to_csv(), file_name='Output.csv', width = "stretch", type ="primary")
    



