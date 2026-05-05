import streamlit as st
import pandas as pd
import plotly.express as px
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Family Travel Tracker", layout="wide")

# --- 2. DATA SOURCE ---
timestamp = int(time.time() // 10) * 10 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vT4HWhDjNmVovOt9nyO5pHGxzfVqJm5wFeosDwtpRSY2HcWPyZHHsttKGmF52pZwGA9qL4rDyc0Nv4C/pub?output=csv&cache_buster={timestamp}"

@st.cache_data(ttl=10)
def load_data():
    # Load the sheet and drop empty columns immediately
    df = pd.read_csv(SHEET_URL, header=0)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Grab headers
    country_col = df.columns[0]
    family_members = [c.strip() for c in df.columns[1:]] # Clean names
    df.columns = [country_col] + family_members # Re-apply cleaned names
    
    # Unpivot
    melted = df.melt(id_vars=[country_col], var_name='Name', value_name='Status')
    melted.columns = ['Country', 'Name', 'Status']
    
    # Clean Status & Filter for 'Yes'
    melted['Status'] = melted['Status'].astype(str).str.strip().str.lower()
    visited = melted[melted['Status'].str.contains('true|yes', na=False)].copy()
    
    # Standardize Country Names
    visited['Country'] = visited['Country'].str.strip()
    
    return visited, family_members

# --- 3. APP INTERFACE ---
try:
    df, all_member_names = load_data()

    st.title("🌍 Family Travel Tracker")

    selected_members = st.multiselect("Select Family Members:", all_member_names, default=all_member_names)

    if selected_members:
        # Filter data
        filtered_df = df[df['Name'].isin(selected_members)].copy()

        if not filtered_df.empty:
            # 1. Create the Grouped Data for the Map
            map_prep = filtered_df.groupby('Country')['Name'].unique().reset_index()
            map_prep['Visitor_Count'] = map_prep['Name'].apply(len)
            map_prep['Visitor_List'] = map_prep['Name'].apply(lambda x: ', '.join(sorted(x)))

            # 2. Logic: If count > 1, it's "Multiple". Otherwise, it's the Name.
            map_prep['Color_By'] = map_prep.apply(
                lambda row: "Multiple Members" if row['Visitor_Count'] > 1 else row['Name'][0], axis=1
            )

            # 3. FORCE THE COLOR MAP
            # We explicitly define the color for every possible name
            palette = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880']
            color_discrete_map = {}
            for i, name in enumerate(all_member_names):
                color_discrete_map[name] = palette[i % len(palette)]
            
            # Add the Black override for overlaps
            color_discrete_map["Multiple Members"] = "#000000"

            # 4. Generate Map
            fig = px.choropleth(
                map_prep,
                locations="Country",
                locationmode="country names",
                color="Color_By", # This MUST match the keys in color_discrete_map
                color_discrete_map=color_discrete_map,
                hover_name="Country",
                hover_data={"Visitor_List": True, "Color_By": False},
                projection="natural earth"
            )

            fig.update_layout(height=600, margin={"r":0,"t":20,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

            # Table
            st.divider()
            st.dataframe(map_prep[['Country', 'Visitor_List']].sort_values('Country'), use_container_width=True, hide_index=True)
        else:
            st.warning("No travel data found. Ensure your sheet has 'Yes' in the cells.")
    else:
        st.info("Pick a name to see the map.")

except Exception as e:
    st.error(f"Something went wrong: {e}")
