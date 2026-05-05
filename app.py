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
    melted['Status'] = melted['Status'].astype(str).str.strip().str.lower()
    # Support for "Yes", "True", or Checkboxes
    visited_data = melted[melted['Status'].str.contains('true|yes', na=False)].copy()
    
    return visited_data[['Name', 'Country']].dropna(), family_cols

try:
    df, all_member_names = load_data()

    st.title("🌍 Family Travel Tracker")

    selected_members = st.multiselect(
        "Select Family Members to Compare:",
        options=all_member_names,
        default=all_member_names
    )

    if selected_members:
        # 1. Filter for selected members
        filtered_df = df[df['Name'].isin(selected_members)]

        # 2. Determine who went where
        # Group by country to see how many (and who) visited
        map_prep = filtered_df.groupby('Country')['Name'].unique().reset_index()
        map_prep['Visitor_Count'] = map_prep['Name'].apply(len)
        map_prep['Visitor_List'] = map_prep['Name'].apply(lambda x: ', '.join(sorted(x)))

        # 3. Create the "Display Category" for coloring
        def get_color_category(row):
            if row['Visitor_Count'] > 1:
                return "Multiple Members"
            else:
                return row['Name'][0] # Returns the single person's name

        map_prep['Display_Category'] = map_prep.apply(get_color_category, axis=1)

        # 4. Define the Custom Color Palette
        # You can customize these hex codes!
        base_colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692']
        color_map = {name: base_colors[i % len(base_colors)] for i, name in enumerate(all_member_names)}
        color_map["Multiple Members"] = "#000000" # Black for overlaps

        # 5. Build the Map
        fig = px.choropleth(
            map_prep,
            locations="Country",
            locationmode="country names",
            color="Display_Category",
            hover_name="Country",
            hover_data={"Visitor_List": True, "Display_Category": False},
            color_discrete_map=color_map,
            title="Travel Map: Colors by Member (Black = Overlap)",
            projection="natural earth"
        )

        fig.update_layout(
            height=600, 
            margin={"r":0,"t":40,"l":0,"b":0},
            legend_title_text='Visitors'
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 6. Detailed Table
        st.divider()
        st.subheader("Travel Details")
        st.dataframe(
            map_prep[['Country', 'Visitor_List', 'Visitor_Count']].sort_values('Visitor_Count', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Please select family members above.")

except Exception as e:
    st.error(f"Error loading map: {e}")
