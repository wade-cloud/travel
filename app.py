import streamlit as st
import pandas as pd
import plotly.express as px
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Family Travel Tracker", layout="wide")

# --- 2. DATA SOURCE ---
# Forces a refresh every 10 seconds to catch sheet edits
timestamp = int(time.time() // 10) * 10 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vT4HWhDjNmVovOt9nyO5pHGxzfVqJm5wFeosDwtpRSY2HcWPyZHHsttKGmF52pZwGA9qL4rDyc0Nv4C/pub?output=csv&cache_buster={timestamp}"

@st.cache_data(ttl=10)
def load_data():
    # Load the sheet
    df = pd.read_csv(SHEET_URL, header=0)
    
    # CRITICAL: Strip spaces from all column headers (names) 
    # and remove any "Unnamed" columns that Google Sheets creates for empty space
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains('^Unnamed|^$')]
    
    country_col = df.columns[0]
    # Every column after the first one is a family member
    family_members = df.columns[1:].tolist()
    
    # "Unpivot" the table
    melted = df.melt(id_vars=[country_col], var_name='Name', value_name='Status')
    melted.columns = ['Country', 'Name', 'Status']
    
    # Clean up Country names and Statuses
    melted['Country'] = melted['Country'].astype(str).str.strip()
    melted['Status'] = melted['Status'].astype(str).str.strip().str.lower()
    
    # Filter for anything that looks like "Yes" or "True" (Checkboxes)
    visited = melted[melted['Status'].str.contains('true|yes|y', na=False)].copy()
    
    return visited, family_members, df

# --- 3. APP INTERFACE ---
try:
    df_visited, all_member_names, raw_df = load_data()

    st.title("🌍 Family Travel Tracker")

    # Show the selector
    selected_members = st.multiselect(
        "Select Family Members:", 
        options=all_member_names, 
        default=all_member_names
    )

    if selected_members:
        # Filter for selected people
        filtered_df = df_visited[df_visited['Name'].isin(selected_members)].copy()

        if not filtered_df.empty:
            # 1. Group Data for the Map
            map_prep = filtered_df.groupby('Country')['Name'].unique().reset_index()
            map_prep['Visitor_Count'] = map_prep['Name'].apply(len)
            map_prep['Visitor_List'] = map_prep['Name'].apply(lambda x: ', '.join(sorted(x)))

            # 2. Logic: Color by Name or "Multiple"
            def assign_color_group(row):
                return "Multiple Members" if row['Visitor_Count'] > 1 else row['Name'][0]

            map_prep['Color_By'] = map_prep.apply(assign_color_group, axis=1)

            # 3. Explicit Color Mapping
            palette = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52']
            color_discrete_map = {name: palette[i % len(palette)] for i, name in enumerate(all_member_names)}
            color_discrete_map["Multiple Members"] = "#000000"

            # 4. Draw Map
            fig = px.choropleth(
                map_prep,
                locations="Country",
                locationmode="country names",
                color="Color_By",
                color_discrete_map=color_discrete_map,
                hover_name="Country",
                hover_data={"Visitor_List": True, "Color_By": False},
                projection="natural earth"
            )

            fig.update_layout(height=600, margin={"r":0,"t":20,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

            # 5. Summary Table
            st.subheader("📍 Where we've been")
            st.dataframe(map_prep[['Country', 'Visitor_List']].sort_values('Country'), use_container_width=True, hide_index=True)
        else:
            st.warning("No travel matches found. Check if your 'Yes' marks are in the right columns!")

    # --- DEBUGGER SECTION ---
    with st.expander("🛠️ Data Debugger (Use this if names are missing)"):
        st.write("These are the family members I found in your Sheet header:")
        st.write(all_member_names)
        st.write("Total 'Yes' entries found per person:")
        st.write(df_visited['Name'].value_counts())
        st.write("Raw data being read (Top 10 rows):")
        st.dataframe(raw_df.head(10))

except Exception as e:
    st.error(f"Error reading data: {e}")
