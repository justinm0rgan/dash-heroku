import pandas as pd
import numpy as np
import os
import geopandas as gpd
from dotenv import load_dotenv
load_dotenv()
from autocensus import Query
import plotly.graph_objs as go
from dash import Dash, callback, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import gunicorn                     #whilst your local machine's webserver doesn't need this, Heroku's linux webserver (i.e. dyno) does. I.e. This is your HTTP server
from whitenoise import WhiteNoise   #for serving static files on Heroku

# set api key
MAPBOX_API = os.getenv("MAPBOX_API")
CENSUS_API = os.getenv("CENSUS_API")

# define external stylesheet
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# fetch data for map
soql_url_map = ('https://data.cityofnewyork.us/resource/nwxe-4ae8.json?' +\
        '$select=boroname,count(tree_id)'+\
        '&$group=boroname').replace(' ', '%20')
soql_map= pd.read_json(soql_url_map)

# configure query for map
query = Query(
    estimate=1,
    years=[2019],
    variables=["B03002_001E"],
    for_geo=['county:005', 'county:047','county:061','county:081','county:085'],
    in_geo=['state:36'],
    # Optional arg to add geometry: 'points', 'polygons', or None (default)
    geometry='polygons',
    # Fill in the following with your actual Census API key
    census_api_key=CENSUS_API
)

# Run query and collect output in dataframe
soql_trees = query.run()

# convert to gdf
gdf = gpd.GeoDataFrame(soql_trees)

# prep for merge
# cond list
conditions=[
    gdf['name'] == "Bronx County, New York",
    gdf['name'] == "Kings County, New York",
    gdf['name'] == "New York County, New York",
    gdf['name'] == "Richmond County, New York",
    gdf['name'] == "Queens County, New York"
]

# value list
values=["Bronx","Brooklyn","Manhattan","Staten Island","Queens"]

# compute with np.select
gdf['boroname'] = np.select(conditions,values)

# merge gdf with soql 
gdf=gdf.merge(soql_map)

# create map plot
trace = go.Choroplethmapbox(geojson=gdf.geometry.__geo_interface__,
                            locations=gdf.index,
                            z=gdf["count_tree_id"],
                            colorscale="Greens",
                            zmin=0,
                            zmax=max(gdf["count_tree_id"]),
                            marker_opacity=0.75,
                            marker_line_width=0,
                            hovertemplate="<b>%{customdata[0]}</b><br><br>" +
                                          "Count of Trees: %{z:,}<br>" +
                                          "<extra></extra>",
                            customdata=gdf[["boroname", "count_tree_id"]])

# Define the layout for the map
layout = go.Layout(
                   mapbox_style="mapbox://styles/mapbox/light-v10",
                   mapbox_zoom=9,
                   mapbox_center={"lat": 40.7, "lon": -73.9},
                   mapbox_accesstoken=MAPBOX_API,
                   margin={"l": 0, "r": 0, "t": 30, "b": 0})

# Create the figure with the trace and layout
map = go.Figure(data=[trace], layout=layout)

# fetch data for bar graph
soql_url = ('https://data.cityofnewyork.us/resource/nwxe-4ae8.json?' +\
        '$select=coalesce(spc_common, "Unknown") as spc_common,boroname,count(tree_id),\
                sum(case when health = "Fair" then 1 else 0 end) as fair_health,\
                sum(case when health = "Good" then 1 else 0 end) as good_health,\
                sum(case when health = "Poor" then 1 else 0 end) as poor_health,\
                round(100 * SUM(CASE WHEN health = "Poor" THEN 1 ELSE 0 END) / COUNT(tree_id),2) AS percent_poor_health,\
                round(100 * SUM(CASE WHEN health = "Fair" THEN 1 ELSE 0 END) / COUNT(tree_id),2) AS percent_fair_health,\
                round(100 * SUM(CASE WHEN health = "Good" THEN 1 ELSE 0 END) / COUNT(tree_id),2) AS percent_good_health' +\
        '&$group=spc_common,boroname').replace(' ', '%20')

# convert to df
df=pd.read_json(soql_url)

# fetch data for grouped bar graph
soql_url_2 = ('https://data.cityofnewyork.us/resource/nwxe-4ae8.json?' +\
        '$select=coalesce(spc_common, "Unknown") as spc_common,boroname,count(tree_id),steward,\
                round(100 * SUM(CASE WHEN health = "Poor" THEN 1 ELSE 0 END) / COUNT(tree_id),2) AS percent_poor_health,\
                round(100 * SUM(CASE WHEN health = "Fair" THEN 1 ELSE 0 END) / COUNT(tree_id),2) AS percent_fair_health,\
                round(100 * SUM(CASE WHEN health = "Good" THEN 1 ELSE 0 END) / COUNT(tree_id),2) AS percent_good_health' +\
        '&$group=spc_common,boroname,steward').replace(' ', '%20')

# convert to df_2
df_2= pd.read_json(soql_url_2)

# create a list of tree species for the dropdown menu
species_list = df['spc_common'].unique()
species_options = [{'label': species, 'value': species} for species in species_list]

# create a list of boroughs for the dropdown menu
borough_list = df['boroname'].unique()
borough_options = [{'label': borough, 'value': borough} for borough in borough_list]


# Instantiate dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# Reference the underlying flask app (Used by gunicorn webserver in Heroku production deployment)
server = app.server 

# Enable Whitenoise for serving static files from Heroku (the /static folder is seen as root by Heroku) 
server.wsgi_app = WhiteNoise(server.wsgi_app, root='static/') 

# define the app layout
app.layout = html.Div([
    html.H1('Tree Health in NYC',style={'text-align': 'center'}),
    html.Div([
        dcc.Markdown(
        '''
        ##### Instructions:
        Select borough by hovering over map area, select tree species from drop-down.
        ''',
        ),
        dcc.Graph(
            id='nyc-county-map',
            figure=map,
            hoverData={'points': [{'customdata': ['Manhattan',0]}]},
        ),

        html.Br(),

        dcc.Markdown(
        '''
        ##### Select Tree Species:
        '''),

        dcc.Dropdown(
            id='species-dropdown',
            options=species_options,
            value=species_list[0],
        ),

        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),

        dcc.Markdown(
        '''
        **Data Source:** [NYC Open Data - 2015 Street Tree Census](https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh)
        ''',
        link_target="_blank"
    ),
    ], style={'display': 'inline-block','float':'left','width': '49%','margin':'20px'}),

    html.Div([
        dcc.Graph(id='health-graph'),
        dcc.Graph(id='steward-graph'),
    ], style={'display': 'inline-block', 'float':'right','width': '49%'}),

])

# define the callback function for the health graph
@app.callback(
    Output('health-graph', 'figure'),
    Input('species-dropdown', 'value'),
    Input('nyc-county-map', 'hoverData')
)
def update_health_graph(species, hoverData):
    borough = hoverData['points'][0]['customdata'][0]
    # filter the data based on the selected species and borough
    df_filtered = df[(df['spc_common'] == species) & (df['boroname'] == borough)]
    good_pct = df_filtered['percent_good_health'].iloc[0]
    fair_pct = df_filtered['percent_fair_health'].iloc[0]
    poor_pct = df_filtered['percent_poor_health'].iloc[0]
    
    # create the bar chart trace
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=['Good', 'Fair', 'Poor'],
            y=[good_pct, fair_pct, poor_pct],
            marker_color=['green', 'orange', 'red'],
            opacity=0.75
        )
   )
    
    # update the layout
    fig.update_layout(
        title=f'Health Status of {species} in {borough}',
        xaxis_title='Health',
        yaxis_title='Percentage (%)',
        bargap=0.1,
        bargroupgap=0.1
    )
    
    # return the figure
    return fig

# define callback section for steward graph
@app.callback(
    Output('steward-graph', 'figure'),
    Input('species-dropdown', 'value'),
    Input('nyc-county-map', 'hoverData')
)

def update_steward_graph(species, hoverData):
    borough = hoverData['points'][0]['customdata'][0]
    # filter the data based on the selected species and borough
    df_2_filtered = df_2[(df_2['spc_common'] == species) & (df_2['boroname'] == borough)]

    # Create the bar chart
    fig = go.Figure()

    # Add the "Poor" health status bar
    fig.add_trace(
        go.Bar(
        x=df_2_filtered['steward'].unique(),
        y=df_2_filtered['percent_poor_health'],
        name='Poor',
        marker_color='red',
        opacity=0.75,
    )
)

    # Add the "Fair" health status bar
    fig.add_trace(
        go.Bar(
        x=df_2_filtered['steward'].unique(),
        y=df_2_filtered['percent_fair_health'],
        name='Fair',
        marker_color='orange',
        opacity=0.75
    )
)

    # Add the "Good" health status bar
    fig.add_trace(
        go.Bar(
        x=df_2_filtered['steward'].unique(),
        y=df_2_filtered['percent_good_health'],
        name='Good',
        marker_color='green',
        opacity=0.75
    )
)

    
# Update the layout
    fig.update_layout(
        title=f'Health Status of {species} by Steward Type in {borough}',
        xaxis_title='Steward Type',
        yaxis_title='Percentage (%)',
        barmode='group',
        bargap=0.15,
        bargroupgap=0.1,
        legend=dict(
            x=0,
            y=1.15,
            orientation='h'
    )
)
    
    # return the figure
    return fig


# Run flask app
if __name__ == "__main__": app.run_server(debug=False, host='0.0.0.0', port=8050)
