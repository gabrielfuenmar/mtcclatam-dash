# -*- coding: utf-8 -*-
"""
Created on Fri Sep 24 14:37:08 2021

@author: snf52211
"""

import pandas as pd
import h3
import json
from geojson.feature import *
import plotly.graph_objs as go
import geopandas as gpd
from shapely import wkt


def list_of_valid_hex(gdf,reso):
    
    exp=[]
    for polygon in gdf.geometry:
        # Convert Polygon to GeoJSON dictionary
        poly_geojson = gpd.GeoSeries([polygon]).__geo_interface__
        # Parse out geometry key from GeoJSON dictionary
        poly_geojson = poly_geojson['features'][0]['geometry'] 
        # Fill the dictionary with Resolution 10 H3 Hexagons

        h3_hexes = h3.polyfill_geojson(poly_geojson, reso)
        exp.append(h3_hexes)
    exp=list(set().union(*exp))
    
    return exp

def sum_by_hexagon(df,resolution,pol,fr,to,vessel_type=[],gt=[]):
    """
    Use h3.geo_to_h3 to index each data point into the spatial index of the specified resolution.
    Use h3.h3_to_geo_boundary to obtain the geometries of these hexagons
    
    Ex counts_by_hexagon(data, 9)
    """
    
    if vessel_type:
        df_aggreg=df[((df.dt_pos_utc.between(fr,to))&(df.StandardVesselType.isin(vessel_type)))]
    else:
        df_aggreg=df[df.dt_pos_utc.between(fr,to)]
    if df_aggreg.shape[0]>0:
        df_aggreg=df_aggreg[df_aggreg.res_9.isin(list_of_valid_hex(pol,9))].reset_index(drop=True)
        
        if gt:
            df_aggreg=df_aggreg[df_aggreg.GrossTonnage.between(gt[0],gt[1])]
    
        if resolution==9:
            df_aggreg = df_aggreg.groupby(by = "res_9").agg({"co2_g":sum,"ch4_g":sum}).reset_index()
        else:
            df_aggreg = df_aggreg.assign(new_res=df_aggreg.res_9.apply(lambda x: h3.h3_to_parent(x,resolution)))
            df_aggreg = df_aggreg.groupby(by = "new_res").agg({"co2_g":sum,"ch4_g":sum}).reset_index()
            
        df_aggreg.columns = ["hex_id", "co2_g","ch4_g"]
            
        df_aggreg["geometry"] =  df_aggreg.hex_id.apply(lambda x: 
                                                                {    "type" : "Polygon",
                                                                      "coordinates": 
                                                                    [h3.h3_to_geo_boundary(x,geo_json=True)]
                                                                }
                                                            )
        
        return df_aggreg
    else:
        return df_aggreg

def hexagons_dataframe_to_geojson(df_hex, file_output = None):
    """
    Produce the GeoJSON for a dataframe that has a geometry column in geojson 
    format already, along with the columns hex_id and value
    
    Ex counts_by_hexagon(data)
    """    
   
    list_features = []
    
    for i,row in df_hex.iterrows():
        feature = Feature(geometry = row["geometry"] , id=row["hex_id"], properties = {"value" : row["value"]})
        list_features.append(feature)
        
    feat_collection = FeatureCollection(list_features)
    
    geojson_result = json.dumps(feat_collection)
    
    #optionally write to file
    if file_output is not None:
        with open(file_output,"w") as f:
            json.dump(feat_collection,f)
    
    return geojson_result 


def choropleth_map(ghg, df_aggreg,layout_in,fill_opacity = 0.5):
    
    """
    Creates choropleth maps given the aggregated data.
    """    
    
    if ghg=="co2":
        ghg="co2_g"
    elif ghg=="ch4":
        ghg="ch4_g"
    else:
        ValueError ("Enter ch4 or co2")
    
    df_aggreg.rename(columns={ghg:"value"},inplace=True)   
    #colormap
    min_value = df_aggreg["value"].min()
    max_value = df_aggreg["value"].max()
    m = round ((min_value + max_value ) / 2 , 0)
    
    #take resolution from the first row
    res = h3.h3_get_resolution(df_aggreg.loc[0,'hex_id'])
    
    #create geojson data from dataframe
    geojson_data = json.loads(hexagons_dataframe_to_geojson(df_hex = df_aggreg))
    
    ##plot on map
    initial_map=go.Choroplethmapbox(geojson=geojson_data,
                                    locations=df_aggreg.hex_id.tolist(),
                                    z=df_aggreg["value"].round(2).tolist(),
                                    colorscale="balance",
                                    marker_opacity=fill_opacity,
                                    marker_line_width=1,
                                    colorbar = dict(thickness=20, ticklen=3,title="grams"),
                                    hovertemplate = '%{z:,.2f}<extra></extra>')
    
    initial_map=go.Figure(data=initial_map,layout=layout_in)
    
    return initial_map
    
