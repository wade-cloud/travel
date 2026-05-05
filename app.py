import streamlit as st
import pandas as pd
import plotly.express as px
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Family Travel Map", layout="wide")

# --- 2. DATA SOURCE ---
# The 'cache_buster' helps force Google Sheets to give us fresh data
timestamp = int(time.time() // 10) * 10 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vT4HWhDjNmVovOt9nyO5pHGxzfVqJm5wFeosDwtpRSY2HcWPyZHHsttKGmF52pZwGA9qL4rDyc0Nv4C/pub?output=csv&cache_buster={timestamp}"

@st.cache_data(ttl=10) # Checks for sheet edits every 10 seconds
def load_data():
    # Load the sheet
    df = pd.read_csv(SHEET_URL, header=0)
    
    # Remove "Unnamed" columns that appear when Google Sheets has empty columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Identify the Country column (Column 0) and Family columns (the rest)
    country_col_name = df.columns[0]
    family_cols = df.columns[1:].tolist()
    
    # "Unpivot" the table from sideways to a long list
    melted = df.melt(
        id_vars=[country_col_name], 
        value_vars=family_cols, 
        var_name='Name', 
        value_name='Status'
    )
    
    # Standardize column names
    melted.columns = ['Country', 'Name', 'Status']
    
    # Clean up the Status column (handles Yes, TRUE, or checkboxes)
    melted['Status'] = melted['Status'].astype(str).str.strip().str.lower()
    visited_data = melted[melted['Status'].str.contains('true|yes', na=False)].copy()
    
    return visited_data[['Name', 'Country']].dropna(), family_cols

# --- 3. APP INTERFACE ---
try:
    df, all_member_names = load_data()

    st.title("🌍 Family Travel Tracker")
    st.write("Edits to your Google Sheet will appear here within 10-60 seconds.")

    # Multiselect for picking family members
    selected_members = st.multiselect(
        "Select Family Members:",
        options=all_member_names,
        default=all_member_names
    )

    if selected_members:
        # Filter data for selected people
        filtered_df = df[df['Name'].isin(selected_members)]

        # Determine who went where
        map_prep = filtered_df.groupby('Country')['Name'].unique().reset_index()
        map_prep['Visitor_Count'] = map_prep['Name'].apply(len)
        map_prep['Visitor_List'] = map_prep['Name'].apply(lambda x: ', '.join(sorted(x)))

        # Assign Category (Specific Name or "Multiple Members")
        def get_color_category(row):
            if row['Visitor_Count'] > 1:
                return "Multiple Members"
            else:
                return row['Name'][0] 

        map_prep['Display_Category'] = map_prep.apply(get_color_category, axis=1)

        # DEFINE CUSTOM COLORS (Black for overlap, various for others)
        base_colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692']
        color_map = {name: base_colors[i % len(base_colors)] for i, name in enumerate(all_member_names)}
        color_map["Multiple Members"] = "#000000" # Forces Black

        # BUILD THE MAP
        fig = px.choropleth(
            map_prep,
            locations="Country",
            locationmode="country names",
            color="Display_Category",
            hover_name="Country",
            hover_data={"Visitor_List": True, "Display_Category": False},
            color_discrete_map=color_map,
            projection="natural earth"
        )

        fig.update_layout(
            height=600, 
            margin={"r":0,"t":20,"l":0,"b":0},
            legend_title_text='Travelers'
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # STATISTICS TABLE
        st.divider()
        st.subheader("📍 Detailed Country List")
        st.dataframe(
            map_prep[['Country', 'Visitor_List', 'Visitor_Count']].sort_values('Visitor_Count', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Select a family member in the dropdown above to start.")

except Exception as e:
    st.error(f"Waiting for data... Ensure your Google Sheet is published and formatted correctly.")
    st.write(f"Technical details: {e}")
