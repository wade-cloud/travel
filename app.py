import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Family Travel Map", layout="wide")

# --- DATA SOURCE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT4HWhDjNmVovOt9nyO5pHGxzfVqJm5wFeosDwtpRSY2HcWPyZHHsttKGmF52pZwGA9qL4rDyc0Nv4C/pub?output=csv"

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(SHEET_URL, header=0)
    country_col_name = df.columns[0]
    family_cols = df.columns[1:].tolist()
    
    melted = df.melt(
        id_vars=[country_col_name], 
        value_vars=family_cols, 
        var_name='Name', 
        value_name='Status'
    )
    
    melted.columns = ['Country', 'Name', 'Status']
    # Handles "Yes", "TRUE", or checkboxes
    melted['Status'] = melted['Status'].astype(str).str.strip().str.lower()
    visited_data = melted[melted['Status'].str.contains('true|yes', na=False)].copy()
    
    return visited_data[['Name', 'Country']].dropna(), family_cols

try:
    df, all_member_names = load_data()

    st.title("🌍 Family Travel Tracker")

    # --- MULTI-SELECT INTERFACE ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_members = st.multiselect(
            "Select Family Members:",
            options=all_member_names,
            default=all_member_names[:2] if len(all_member_names) > 1 else all_member_names
        )

    with col2:
        mode = st.radio(
            "Filter Logic:",
            ["Show Anyone's (OR)", "Show Shared (AND)"],
            help="OR: Show countries visited by at least one selected person. AND: Show countries where EVERY selected person has been."
        )

    if selected_members:
        # Filter data for selected people
        filtered_df = df[df['Name'].isin(selected_members)]

        if "AND" in mode:
            # Logic: Group by country and count unique names. 
            # If count == number of selected members, they all went.
            counts = filtered_df.groupby('Country')['Name'].nunique()
            shared_countries = counts[counts == len(selected_members)].index
            display_df = filtered_df[filtered_df['Country'].isin(shared_countries)].copy()
            color_scale = "Purples"
        else:
            display_df = filtered_df.copy()
            color_scale = "Greens"

        # Prepare Map Data
        map_data = display_df.groupby('Country').agg({
            'Name': [('Count', 'count'), ('Who', lambda x: ', '.join(sorted(x.unique())))]
        }).reset_index()
        map_data.columns = ['Country', 'Visit Count', 'Names']

        # --- DRAW MAP ---
        fig = px.choropleth(
            map_data,
            locations="Country",
            locationmode="country names",
            color="Visit Count",
            hover_name="Country",
            hover_data={"Names": True, "Visit Count": True},
            color_continuous_scale=color_scale,
            projection="natural earth"
        )
        
        fig.update_layout(height=600, margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)

        # --- STATS TABLE ---
        st.divider()
        st.subheader(f"📊 Countries visited by {', '.join(selected_members)}")
        st.dataframe(
            map_data.sort_values('Visit Count', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Please select at least one family member to see the map.")

except Exception as e:
    st.error(f"Error connecting to data: {e}")
