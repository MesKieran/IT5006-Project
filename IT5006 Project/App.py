import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import json
import plotly.express as px

st.set_page_config(page_title="IT5006 Project", page_icon=":smiley:", layout="wide")

# Load data
df_rental = pd.read_csv('./Cleaned_data/rental_cleaned.csv', parse_dates=['rent_approval_date'])
df_resale = pd.read_csv('./Cleaned_data/resale_data_cleaned.csv', parse_dates=['month'])

# Sidebar + Filters
# st.sidebar.success("Select a page above")
rental_resale_sltn = st.sidebar.radio(
    'HDB Rental or Resale?',
    ("Rental", "Resale")
    )
if rental_resale_sltn == 'Rental':
    min_sltn_value = pd.to_datetime(df_rental['rent_approval_date'].min()).year
    max_sltn_value = pd.to_datetime(df_rental['rent_approval_date'].max()).year
else: 
    min_sltn_value = pd.to_datetime(df_resale['month'].min()).year
    max_sltn_value = pd.to_datetime(df_resale['month'].max()).year

date_sltn = st.sidebar.slider(
    'Select date range',
    min_sltn_value, max_sltn_value, (min_sltn_value,max_sltn_value)
    )

# Header
st.subheader("Welcome to IT5006 Project")
st.title("HDB Data - Exploratory Data Analysis")

# Loading the selected dataset to dataframe based on filters
if rental_resale_sltn == 'Rental':
  df = df_rental.iloc[:, 1:]     # Drop first column
  df = df[(df['rent_approval_date'].dt.year >= date_sltn[0]) & (df['rent_approval_date'].dt.year <= date_sltn[1])]
else:
  df = df_resale
  df = df[(df['month'].dt.year >= date_sltn[0]) & (df['month'].dt.year <= date_sltn[1])]


# Common visualisations

## Display details of dataset
st.write('### Summary of Data')
if rental_resale_sltn == 'Rental':
  median_price = df['monthly_rent'].median()
  min_price = df['monthly_rent'].min()
  max_price = df['monthly_rent'].max()
else: 
  median_price = df['resale_price'].median()
  min_price = df['resale_price'].min()
  max_price = df['resale_price'].max()
no_units = len(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Median price", f'S${median_price:,.0f}')
col2.metric("Min price", f'S${min_price:,.0f}')
col3.metric("Max price", f'S${max_price:,.0f}')
col4.metric("No of units", f'{no_units:,}')

st.write('### Data Analysis')

# Function to load and preprocess data based on user selection (For zach's visualisation)
def load_and_preprocess_data(data_type, selected_year_start, selected_year_end, geojson_data):
    # Load data based on the selected type
    if data_type == 'Resale':
        data = pd.read_csv('./Cleaned_data/resale_data_cleaned.csv', parse_dates=['month'])
        data['year'] = data['month'].dt.year
    else:
        data = pd.read_csv('./Cleaned_data/rental_cleaned.csv', parse_dates=['rent_approval_date'])
        data['year'] = data['rent_approval_date'].dt.year
        data['price_per_sqm'] = data['monthly_rent']

    data['town'] = data['town'].str.upper()

    # Filter data for the selected year
    data = data[(data['year'] >= selected_year_start) & (data['year'] <= selected_year_end)]

    # Extract town names from GeoJSON
    geojson_towns = [feature['properties']['name'] for feature in geojson_data['features']]
    
    # Filter dataframe to only include towns found in the GeoJSON
    data = data[data['town'].isin(geojson_towns)]

    # Aggregate data
    if data_type == 'Resale':
        aggregated_data = data.groupby('town')['price_per_sqm'].mean().reset_index()
    else:
        aggregated_data = data.groupby('town')['price_per_sqm'].mean().reset_index()

    # Create a dataframe for towns in GeoJSON but missing in data
    aggregated_data_towns = set(aggregated_data['town'])
    missing_towns = [town for town in geojson_towns if town not in aggregated_data_towns]
    missing_df = pd.DataFrame({'town': missing_towns, 'price_per_sqm': [0] * len(missing_towns)})

    # Combine aggregated data with missing towns
    final_df = pd.concat([aggregated_data, missing_df], ignore_index=True)

    return final_df


# Function to create choropleth map
def make_choropleth(input_df, geojson_data):
    # Define a more granular color scale
    custom_color_scale = [
        [0, "rgb(194,197,204)"],  # White for NaN or values outside the expected range
        [1/27, "rgb(240,249,232)"],  # Lightest green
        [2/27, "rgb(204,235,197)"],
        [3/27, "rgb(168,221,181)"],
        [4/27, "rgb(123,204,196)"],
        [5/27, "rgb(78,179,211)"],
        [6/27, "rgb(43,140,190)"],
        [7/27, "rgb(8,104,172)"],
        [8/27, "rgb(8,64,129)"],  # Blue
        [9/27, "rgb(39,100,125)"],
        [10/27, "rgb(60,130,142)"],
        [11/27, "rgb(85,158,131)"],
        [12/27, "rgb(107,184,104)"],
        [13/27, "rgb(137,204,74)"],  # Green-Yellow
        [14/27, "rgb(192,217,59)"],
        [15/27, "rgb(217,234,43)"],
        [16/27, "rgb(237,248,33)"],  # Yellow
        [17/27, "rgb(252,217,125)"],
        [18/27, "rgb(252,186,3)"],
        [19/27, "rgb(252,153,0)"],  # Orange
        [20/27, "rgb(252,129,0)"],
        [21/27, "rgb(252,104,0)"],
        [22/27, "rgb(252,78,42)"],
        [23/27, "rgb(241,58,19)"],  # Red
        [24/27, "rgb(224,33,0)"],
        [25/27, "rgb(204,12,0)"],
        [26/27, "rgb(180,0,0)"],  # Darker red
        [1.0, "rgb(160,0,0)"]  # Darkest red
    ]
    choropleth = px.choropleth(input_df,
                               geojson=geojson_data,
                               locations='town',
                               featureidkey="properties.name",
                               color='price_per_sqm',
                               color_continuous_scale=custom_color_scale,
                               labels={'price_per_sqm': 'Price per sqm'})
    choropleth.update_geos(fitbounds="locations", visible=False)

    # Disable zoom and pan
    choropleth.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=750, width=650,
        dragmode=False,
        geo=dict(
            projection_scale=5, # Keep this or adjust as needed for initial scale
            center=dict(lat=1.3521, lon=103.8198), # Centering on Singapore, adjust as needed
        )
    )

    return choropleth

# Function to map values to colors based on the custom color scale used for the choropleth
def map_value_to_color(value, min_value, max_value):
    # Define the custom color scale as used in the choropleth
    custom_color_scale = [
        "rgb(255, 255, 255)",  # White for NaN or values outside the expected range
        "rgb(240, 249, 232)",  # Lightest green
        "rgb(204, 235, 197)",
        "rgb(168, 221, 181)",
        "rgb(123, 204, 196)",
        "rgb(78, 179, 211)",
        "rgb(43, 140, 190)",
        "rgb(8, 104, 172)",
        "rgb(8, 64, 129)",  # Blue
        "rgb(39, 100, 125)",
        "rgb(60, 130, 142)",
        "rgb(85, 158, 131)",
        "rgb(107, 184, 104)",
        "rgb(137, 204, 74)",  # Green-Yellow
        "rgb(192, 217, 59)",
        "rgb(217, 234, 43)",
        "rgb(237, 248, 33)",  # Yellow
        "rgb(252, 217, 125)",
        "rgb(252, 186, 3)",
        "rgb(252, 153, 0)",  # Orange
        "rgb(252, 129, 0)",
        "rgb(252, 104, 0)",
        "rgb(252, 78, 42)",
        "rgb(241, 58, 19)",  # Red
        "rgb(224, 33, 0)",
        "rgb(204, 12, 0)",
        "rgb(180, 0, 0)",  # Darker red
        "rgb(160, 0, 0)"   # Darkest red
    ]
    
    # Handle NaN values by returning a default color, e.g., grey
    if pd.isnull(value):
        return "rgb(128, 128, 128)"  # Grey for NaN or missing values
    
    # Normalize the value within the range
    normalized_value = (value - min_value) / (max_value - min_value)
    # Ensure the normalized value is within [0, 1] after handling edge cases
    normalized_value = max(0, min(normalized_value, 1))
    # Map the normalized value to an index in the color scale
    color_index = int(normalized_value * (len(custom_color_scale) - 1))
    return custom_color_scale[color_index]
def plot_additional_graphs(data_type, selected_year_start, selected_year_end):
    if data_type == 'Resale':
        data = pd.read_csv('./Cleaned_data/resale_data_cleaned.csv', parse_dates=['month'])
        data['year'] = data['month'].dt.year
        data['town'] = data['town'].str.upper()
        data = data[(data['year'] >= selected_year_start) & (data['year'] <= selected_year_end)]
        
        # Graph 1: Price per sqm against flat type
        plt.figure(figsize=(10, 6))
        data.groupby('flat_type')['price_per_sqm'].mean().plot(kind='bar', color='skyblue')
        plt.title('Price per Sqm by Flat Type')
        plt.ylabel('Average Price per Sqm')
        plt.xlabel('Flat Type')
        st.pyplot(plt)
        plt.clf()  # Clear the figure after plotting
        
        # Graph 2: Price per sqm over the selected year, aggregated by months (if needed)
        # Assuming you want to show variations within the selected year. 
        # This requires a different approach, considering your data spans multiple years.
        
        # If you intended to show changes over the years, consider removing the year filter for this graph.
        plt.figure(figsize=(10, 6))
        # Ensure there's data to plot
        if not data.empty:
            data.groupby(data['month'].dt.strftime('%Y-%m'))['price_per_sqm'].mean().plot(kind='line', color='green')
            plt.title('Price per Sqm Over Months between ' + str(selected_year_start) + ' and ' + str(selected_year_end) )
            plt.ylabel('Average Price per Sqm')
            plt.xlabel('Month')
            st.pyplot(plt)
        else:
            st.write("No data available for this year.")
        plt.clf()  # Clear the figure after plotting
        
        # Graph 3: Number of flats sold against towns
        plt.figure(figsize=(10, 6))
        data['town'].value_counts().plot(kind='bar', color='orange')
        plt.title('Number of Flats Sold by Town')
        plt.ylabel('Number of Flats Sold')
        plt.xlabel('Town')
        st.pyplot(plt)
        plt.clf()  # Clear the figure after plotting
        
        # Graph 4: Number of flats sold against flat type
        plt.figure(figsize=(10, 6))
        data['flat_type'].value_counts().plot(kind='bar', color='teal')
        plt.title('Number of Flats Sold by Flat Type')
        plt.ylabel('Number of Flats Sold')
        plt.xlabel('Flat Type')
        st.pyplot(plt)
        plt.clf()  # Clear the figure after plotting

## TO DO: insert common visualisations here


# Additional visualisations for resale
if rental_resale_sltn == 'Resale':
  # TO DO: Show additional visualisations
  st.title("HDB Price Dashboard For Resale Flats ")

  # Load GeoJSON file
  geojson_file = "map4.json"
  with open(geojson_file) as f:
      sg_geojson = json.load(f)

  # Data Loading and Processing with GeoJSON towns considered
  df = load_and_preprocess_data(rental_resale_sltn, date_sltn[0], date_sltn[1], sg_geojson)

  sg_map = make_choropleth(df, sg_geojson)
  st.plotly_chart(sg_map, use_container_width=False)

  # Plot additional graphs if data type is 'Resale'
  plot_additional_graphs(rental_resale_sltn, date_sltn[0], date_sltn[1])

# For rental data
else:
  st.title("HDB Price Dashboard For Rental Flats ")
  # Load GeoJSON file
  geojson_file = "map4.json"
  with open(geojson_file) as f:
      sg_geojson = json.load(f)

  # Data Loading and Processing with GeoJSON towns considered
  df = load_and_preprocess_data(rental_resale_sltn, date_sltn[0], date_sltn[1], sg_geojson)

  sg_map = make_choropleth(df, sg_geojson)
  st.plotly_chart(sg_map, use_container_width=False)


# Display dataset at bottom of page
st.write('### Data')
st.write(df)

_ = '''
with st.container():
  st.write("---")
  left_column, right_column = st.columns(2)
  with left_column:
    st.header("Exploartory Data Analysis")
    st.write("##")
    st.write(
      """
      content
      """
    )
  with right_column:
    # df.head()
'''
