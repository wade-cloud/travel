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
    # Load the sheet
    df = pd.read_csv(SHEET_URL)
    
    # Check how many columns we actually have
    actual_col_count = len(df.columns)
    
    if actual_col_count >= 2:
        # Take ONLY the first two columns, no matter how many exist
        df = df.iloc[:, [0, 1]] 
        # Force rename them so the rest of the code works
        df.columns = ['Name', 'Country']
    else:
        # If the sheet is empty or only has 1 column, create an empty structure
        return pd.DataFrame(columns=['Name', 'Country'])
        
    # Clean up: remove any rows where Name or Country is missing
    df = df.dropna(subset=['Name', 'Country'])
    
    return df

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
