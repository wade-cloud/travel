import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Family Travel Map", layout="wide")

# --- DATA SOURCE ---
# Using the CSV link you provided
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT4HWhDjNmVovOt9nyO5pHGxzfVqJm5wFeosDwtpRSY2HcWPyZHHsttKGmF52pZwGA9qL4rDyc0Nv4C/pub?output=csv"

@st.cache_data(ttl=300)
def load_data():
    # 1. Load the sheet 
    # We use header=0 to tell Python the first row IS the name of the columns
    df = pd.read_csv(SHEET_URL, header=0)
    
    # 2. Identify the Country column (should be the very first one)
    country_col_name = df.columns[0]
    
    # 3. Identify Family Member columns (everything EXCEPT the first column)
    family_cols = df.columns[1:].tolist()
    
    # 4. "Unpivot" the table
    # This takes names from the top and puts them into a 'Name' column
    melted = df.melt(
        id_vars=[country_col_name], 
        value_vars=family_cols, 
        var_name='Name', 
        value_name='Status'
    )
    
    # 5. Clean up column names for the rest of the app
    melted.columns = ['Country', 'Name', 'Status']
    
    # 6. Filter for 'Yes' (ignoring spaces or capitalization)
    melted['Status'] = melted['Status'].astype(str).str.strip().str.lower()
    visited_data = melted[melted['Status'] == 'yes'].copy()
    
    # 7. Final cleanup of the data
    visited_data = visited_data[['Name', 'Country']].dropna()
    
    return visited_data

# --- APP LOGIC ---
try:
    df = load_data()
    family_members = sorted(df['Name'].unique())

    # HEADER
    st.title("🌍 Family Travel Tracker")
    st.markdown("Select a family member to see their travels, or 'Family Heatmap' for the cumulative view.")

    # TOP NAVIGATION
    # Using columns to create a "Button Bar" effect
    cols = st.columns(len(family_members) + 1)
    
    # We use session_state to track which button was clicked
    if 'view' not in st.session_state:
        st.session_state.view = 'Family Heatmap'

    if cols[0].button("👪 Family Heatmap"):
        st.session_state.view = 'Family Heatmap'
    
    for i, member in enumerate(family_members):
        if cols[i+1].button(member):
            st.session_state.view = member

    # --- MAP SECTION ---
    if st.session_state.view == 'Family Heatmap':
        # Count unique people per country
        map_df = df.groupby('Country').count().reset_index()
        map_df.columns = ['Country', 'Total Visitors']
        
        # Get names for hover data
        names_df = df.groupby('Country')['Name'].apply(lambda x: ', '.join(x)).reset_index()
        map_df = map_df.merge(names_df, on='Country')
        
        fig = px.choropleth(
            map_df,
            locations="Country",
            locationmode="country names",
            color="Total Visitors",
            hover_name="Country",
            hover_data={"Name": True, "Total Visitors": True},
            color_continuous_scale="Greens",
            projection="natural earth"
        )
    else:
        # Individual View
        member_df = df[df['Name'] == st.session_state.view].copy()
        member_df['Visited'] = 1
        
        fig = px.choropleth(
            member_df,
            locations="Country",
            locationmode="country names",
            color="Visited",
            hover_name="Country",
            color_continuous_scale="Blues",
            projection="natural earth"
        )
        fig.update_layout(coloraxis_showscale=False)

    fig.update_layout(height=600, margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

    # --- LISTS UNDER THE MAP ---
    st.divider()
    st.subheader(f"📊 Details: {st.session_state.view}")

    if st.session_state.view == 'Family Heatmap':
        # Show table of most visited to least visited
        summary = df.groupby('Country')['Name'].agg(['count', ', '.join]).reset_index()
        summary.columns = ['Country', 'Count', 'Who Has Been']
        summary = summary.sort_values(by='Count', ascending=False)
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        # Just show that person's list
        my_list = df[df['Name'] == st.session_state.view]['Country'].sort_values()
        st.write(f"Total Countries Visited: **{len(my_list)}**")
        st.table(my_list)

except Exception as e:
    st.error(f"Waiting for data... Check if your Google Sheet is published and has rows. Error: {e}")
