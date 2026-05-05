import streamlit as st
import pandas as pd
import plotly.express as px
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Family Travel Map", layout="wide")

# --- 2. DATA SOURCE ---
timestamp = int(time.time() // 10) * 10 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vT4HWhDjNmVovOt9nyO5pHGxzfVqJm5wFeosDwtpRSY2HcWPyZHHsttKGmF52pZwGA9qL4rDyc0Nv4C/pub?output=csv&cache_buster={timestamp}"

@st.cache_data(ttl=10)
def load_data():
    df = pd.read_csv(SHEET_URL, header=0)
    
    # Remove "Unnamed" columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    country_col_name = df.columns[0]
    family_cols = df.columns[1:].tolist()
    
    # Unpivot table
    melted = df.melt(
        id_vars=[country_col_name], 
        value_vars=family_cols, 
        var_name='Name', 
        value_name='Status'
    )
    
    melted.columns = ['Country', 'Name', 'Status']
    
    # Clean Status
    melted['Status'] = melted['Status'].astype(str).str.strip().str.lower()
    visited_data = melted[melted['Status'].str.contains('true|yes', na=False)].copy()
    
    # --- COUNTRY NAME FIXER ---
    # Common spreadsheet names mapped to official Map names
    replacements = {
        "USA": "United States",
        "United States of America": "United States",
        "UK": "United Kingdom",
        "UAE": "United Arab Emirates",
        "South Korea": "Korea, Republic of",
        "Vietnam": "Viet Nam"
    }
    visited_data['Country'] = visited_data['Country'].str.strip().replace(replacements)
    
    return visited_data[['Name', 'Country']].dropna(), family_cols

# --- 3. APP INTERFACE ---
try:
    df, all_member_names = load_data()

    st.title("🌍 Family Travel Tracker")

    selected_members = st.multiselect(
        "Select Family Members:",
        options=all_member_names,
        default=all_member_names
    )

    if selected_members:
        filtered_df = df[df['Name'].isin(selected_members)]

        if not filtered_df.empty:
            # Grouping logic
            map_prep = filtered_df.groupby('Country')['Name'].unique().reset_index()
            map_prep['Visitor_Count'] = map_prep['Name'].apply(len)
            map_prep['Visitor_List'] = map_prep['Name'].apply(lambda x: ', '.join(sorted(x)))

            # Categorization for coloring
            def get_color_category(row):
                if row['Visitor_Count'] > 1:
                    return "Multiple Members"
                else:
                    return str(row['Name'][0]) 

            map_prep['Display_Category'] = map_prep.apply(get_color_category, axis=1)

            # --- COLOR ENGINE ---
            # Distinct colors for up to 10 members
            palette = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52']
            color_map = {name: palette[i % len(palette)] for i, name in enumerate(all_member_names)}
            color_map["Multiple Members"] = "#000000" # Black for overlaps

            fig = px.choropleth(
                map_prep,
                locations="Country",
                locationmode="country names",
                color="Display_Category",
                hover_name="Country",
                hover_data={"Visitor_List": True, "Display_Category": False, "Country": False},
                color_discrete_map=color_map,
                projection="natural earth"
            )

            fig.update_layout(
                height=600, 
                margin={"r":0,"t":20,"l":0,"b":0},
                legend_title_text='Travelers'
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # Details Table
            st.divider()
            st.subheader("📍 Travel Breakdown")
            st.dataframe(
                map_prep[['Country', 'Visitor_List', 'Visitor_Count']].sort_values('Visitor_Count', ascending=False),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No 'Yes' entries found for the selected members.")
    else:
        st.info("Please select at least one family member.")

except Exception as e:
    st.error(f"Error: {e}")
