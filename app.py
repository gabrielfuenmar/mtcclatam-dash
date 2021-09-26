
'''
Author:Gabriel Fuentes
gabriel.fuentes@snf.no'''

# Import required libraries
import pathlib
import dash
import numpy as np
from dash.dependencies import Input, Output, State, ClientsideFunction
import dash_core_components as dcc
import dash_html_components as html
import plotly.figure_factory as ff
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from dateutil.relativedelta import *
from datetime import datetime

from controls import TYPE_COLORS,PORTS_COLORS,FLEET
from choropleth_map_emission import choropleth_map, sum_by_hexagon

##DataFrames
from data_filtering import processed_data
import pandas as pd
import geopandas as gpd
import os
import requests

##Databases
##Databases
panama_ports=gpd.read_file("data/Panama_ports.geojson")

canal,ports=processed_data(FLEET)
gatun=pd.read_csv("data/draught_restr_data.csv")

em=pd.read_csv("data/emissions_type_monthly.csv")
em["dt_pos_utc"]=pd.to_datetime(em["dt_pos_utc"])

pol=gpd.read_file("data/Panama_Canal.geojson")[["Name","geometry"]]
pol=pol[pol.geometry.apply(lambda x: x.geom_type=="Polygon")]

##Transform to datetime. Preferred to read csv method which is less flexible.

canal["time_at_entrance"]=pd.to_datetime(canal["time_at_entrance"])
ports["initial_service"]=pd.to_datetime(ports["initial_service"])
gatun["Date"]=pd.to_datetime(gatun["Date"])

##Ports color
panama_ports=panama_ports.assign(color="#F9A054")

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)

app.title = 'Panama Maritime Stats'

server = app.server

# Create global chart template

MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN', None)

layout_map = dict(
    autosize=True,
    paper_bgcolor='#30333D',
    plot_bgcolor='#30333D',
    margin=dict(l=10, r=10, b=10, t=40),
    hovermode="closest",
    font=dict(family="HelveticaNeue",size=17,color="#B2B2B2"),
    legend=dict(font=dict(size=10), orientation="h"),
    title="<b>Emissions Review</b>",
    mapbox=dict(
        accesstoken=MAPBOX_TOKEN,
        style='mapbox://styles/gabrielfuenmar/ckhs87tuj2rd41amvifhb26ad',
        center=dict(lon=-79.55, lat=8.93),
        zoom=9,
    ),
    showlegend=False,
)

layout= dict(
    legend=dict(bgcolor='rgba(0,0,0,0)',font=dict(size=14,family="HelveticaNeue")),
    font_family="HelveticaNeue",
    font_color="#B2B2B2",
    title_font_family="HelveticaNeue",
    title_font_color="#B2B2B2",
    title_font_size=20,
    paper_bgcolor='#21252C',
    plot_bgcolor='#21252C',
    xaxis=dict(gridcolor="rgba(178, 178, 178, 0.1)",title_font_size=15,
               tickfont_size=14,title_font_family="HelveticaNeue",tickfont_family="HelveticaNeue"),
    yaxis=dict(gridcolor="rgba(178, 178, 178, 0.1)",title_font_size=15,tickfont_size=14,
               title_font_family="HelveticaNeue",tickfont_family="HelveticaNeue")
    )

##Modebar on graphs
config={"displaylogo":False, 'modeBarButtonsToRemove': ['autoScale2d']}


##Annotation on graphs
annotation_layout=dict(
    xref="x domain",
    yref="y domain",
    x=0.25,
    y=-0.35)

# Create app layout
app.layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.A(html.Img(
                            src=app.get_asset_url("mtcc_logo_v3.png"),
                            id="plotly-image",
                            style={
                                "height": "160px",
                                "width": "auto",
                                "margin-bottom": "0px",
                                "text-align": "center"
                            },
                        ),
                            href="https://mtcclatinamerica.com/")
                    ],
                    className="one-half column",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "Panama Maritime Statistics",
                                    style={"margin-bottom": "0px"},
                                ),
                                html.H5(
                                    "Efficiency and Sustainability Indicators", style={"margin-top": "0px"}
                                ),
                            ]
                        )
                    ],
                    className="one-half column",
                    id="title",
                ),
                html.Div(
                    [
                        html.Button("Refresh", id="refresh-button"), 
                        html.A(
                            html.Button("Developer", id="home-button"),
                            href="https://gabrielfuentes.org",
                        )                  
                    ],
                    className="one-third column",
                    id="button",
                    style={
                        "text-align": "center"},
                ),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "15px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                      html.P("Date Filter",
                                    className="control_label",
                                ),
                                html.Div([html.P(id="date_from"),
                                html.P(id="date_to")],className="datecontainer")
                            ,
                        dcc.RangeSlider(
                            id="year_slider",
                            min=0,
                            max=20,
                            value=[0, 20],
                            marks={
                                0:"Dec 2018",
                                5:"May 2019",
                                10:"Oct 2019",
                                15:"Mar 2020",
                                20:"Aug 2020"},
                            allowCross=False,
                            className="dcc_control",
                        ),
                        html.P("Vessel Type:", className="control_label"),
                        dcc.Dropdown(
                            id='types-dropdown',
                            options=[{'label': row,'value': row} \
                                     for row in sorted(FLEET)],
                                    placeholder="All",multi=True,
                                    className="dcc_control"),
                        html.P("Port:", className="control_label"),
                        dcc.Dropdown(
                            id='ports-dropdown',
                            options=[{'label': row,'value': row} \
                                     for row in sorted(ports[~ports.port_name.isin(["Pacific - PATSA","Colon2000"])]\
                                                             .dropna(subset=["port_name"]).port_name.unique())+["Panama Canal South", "Panama Canal North"]],
                                    placeholder="All",multi=True,
                                    className="dcc_control"),
                        html.P(
                            "Vessel Size (GT)",
                            className="control_label",
                        ),
                        html.Div([html.P(id="size_from"),
                                html.P(id="size_to")],className="datecontainer"),
                        
                        dcc.RangeSlider(
                            id="size_slider",
                            min=400,
                            max=170000,
                            value=[400, 170000],
                            step=8500,
                            marks={
                                400:"400",
                                35000:"35k",
                                70000:"70k",
                                105000:"105k",
                                140000:"140k",
                                170000:"170k"},
                            allowCross=False,
                            className="dcc_control",
                        ),
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="waitingText"), html.P("Waiting Average")],
                                    id="waiting",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="opsText"), html.P("Operations")],
                                    id="ops",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="serviceText"), html.P("Service Average")],
                                    id="service_m",
                                    className="mini_container",
                                ),
                                html.Div(#####Hardcoded for the time being. Build a scrapper.
                                    [html.H6(["15.24 m"],id="draughtText"), html.P("Canal Max Draught TFW")],
                                    id="draught",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        html.Div([
                            html.Div(
                                    [
                                        html.Div([html.H5("Emissions Review"),
                                                  html.H6(id="month_map",style={"color":"white"})],
                                                            style={"display": "flex", "flex-direction": "row","justify-content":"space-between"}),
                                        dcc.Graph(animate=False,config=config,id="map_in"),
                                             html.P(["Grid size"],id="grid_size",className="control_label"),
                                                         dcc.Slider(
                                                         id="zoom_slider",
                                                         min=4,
                                                         max=8,
                                                         value=8,
                                                         marks={
                                                            4:{'label': '1'},5:{'label': '2'},6:{'label': '3'},
                                                            7:{'label': '4'},8:{'label': '5'}},
                                                         className="dcc_control",
                                                         included=False),
                                                             dcc.RadioItems(
                                                             id='selector',options=[{'label': "CO2 emissions", 'value': "co2"},
                                                                                    {'label': "CH4 emissions", 'value': "ch4"}],
                                                             value="co2",labelStyle={'display': 'inline-block'}),
                                           ],
                                id="emissionsMapContainer",
                                className="pretty_container eight columns",
                                )
                            ],
                            className="row flex-display",
                            ),
                        ],
                    id="right-column",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="service_graph",config=config)],
                    className="pretty_container six columns",
                ),
                html.Div(
                    [dcc.Graph(id="waiting_graph",config=config)],
                    className="pretty_container six columns",
                )
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="draught_graph",config=config)],
                    className="pretty_container six columns",
                ),
                html.Div(
                    [dcc.Graph(id="ratio_graph",config=config)],
                    className="pretty_container six columns",
                ),
            ],
            className="row flex-display",
        ),
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

    
def upper_text_p1(fr="01-01-2019",to="18-11-2020",ports_sel=["All"],
                type_vessel=["All"],size=["All"],text_bar=True,*args):
    
    date_from=pd.to_datetime(fr)
    date_to=pd.to_datetime(to)
    
    canal_in=canal[(canal.time_at_entrance.between(date_from,date_to))&(canal.direct_transit_boolean==True)].\
        copy()
    ports_in=ports[ports.initial_service.between(date_from,date_to)].\
        copy()
    canal_in=canal_in.assign(day=canal_in.time_at_entrance.dt.date)
    canal_in=canal_in[["day","waiting_time","service_time","port_name","draught_ratio","StandardVesselType","GT"]]
    canal_in["day"]=pd.to_datetime(canal_in.day)
    ports_in=ports_in.assign(day=ports_in.initial_service.dt.date)
    ports_in=ports_in[["day","waiting_time","service_time","port_name","draught_ratio","StandardVesselType","GT"]]
    ports_in["day"]=pd.to_datetime(ports_in.day)
    
    df_in=pd.concat([ports_in,canal_in],axis=0)
    
    if "All" not in ports_sel:
        df_in=df_in[df_in.port_name.isin(ports_sel)]
    
    if "All" not in size:
        df_in=df_in[df_in.GT.between(size[0],size[1])]
        
    if "All" not in type_vessel:
        df_in=df_in[df_in["StandardVesselType"].isin(type_vessel)]
        
    if text_bar is True: ##Row at top with summary values
        waiting_mean=df_in.waiting_time.mean()
        ops=df_in.shape[0]
        service_mean=df_in.service_time.mean()

        return waiting_mean,ops,service_mean
    
    else: ###Graphs on waiting, service time and draught ratio
        
        ##Fig ratio
        df_in=df_in[df_in.day>pd.to_datetime("01-01-2019")]
        df_in=df_in.reset_index(drop=True)
        series_grouped=[]
        for name,row in df_in.\
        groupby([df_in.day.dt.isocalendar().week,df_in.day.dt.year,"StandardVesselType"]):
            series_grouped.append([pd.to_datetime(str(name[1])+"-"+str(name[0])+"-1",format='%Y-%W-%w'),name[2],row.draught_ratio.mean()])
        
        series_grouped=pd.DataFrame(series_grouped,columns=["day","StandardVesselType","draught_ratio"]).sort_values(by=["day"])
        
        draught_fig = go.Figure()
        
        for val in series_grouped["StandardVesselType"].unique():
            series_in=series_grouped[series_grouped["StandardVesselType"]==val]
            draught_fig.add_trace(go.Scatter(
                name=val,
                mode="markers+lines",
                x=series_in.day,y=series_in.draught_ratio,
                line=dict(shape="spline", width=1, color=TYPE_COLORS[val]),
                marker=dict(symbol="diamond-open")))
        
        
        draught_fig.update_layout(layout,legend=dict(x=1),title_text="<b>Draught Ratio per vessel type</b>",
                                  xaxis=dict(title_text="Date"),yaxis=dict(title_text="Ratio"),)
        draught_fig.add_annotation(annotation_layout,text="*AIS draft/min(maxTFWD, max Allowable draft)")
        ##Service and waiting time
        labels_w=[]
        remove_w=[]
        waiting=[]
        
        for name,row in df_in.groupby("port_name"):
            if len(row.waiting_time.dropna().tolist())>25:      
                labels_w.append(name)
                wa_li=row.waiting_time[(row.waiting_time>1)&(row.waiting_time<row.waiting_time.quantile(0.95))&\
                                       (row.waiting_time>row.waiting_time.quantile(0.05))]
                waiting.append(wa_li.dropna().tolist())
            else:
                remove_w.append(name)
                
        labels_s=[]
        remove_s=[]
        service=[]
    
        
        for name,row in df_in.groupby("port_name"):
            if len(row.service_time.dropna().tolist())>25:  
                labels_s.append(name)
                se_li=row.service_time[(row.service_time>0)&(row.service_time<row.service_time.quantile(0.95))&\
                       (row.service_time>row.service_time.quantile(0.05))]
                service.append(se_li.dropna().tolist())
            else:
                remove_s.append(name)
             
        ##Figs of waiting and service time
        
        if len(labels_w)>0:
            fig_waiting = ff.create_distplot(waiting, labels_w,histnorm="probability density",colors=list(PORTS_COLORS.values()),show_rug=False,show_curve=False)
            
        else:
            fig_waiting=go.Figure()
            fig_waiting.add_annotation(x=2,y=5,xref="x",yref="y",text="max=5",showarrow=True,
            font=dict(family="Courier New, monospace",size=16, color="#ffffff"),align="center",
            arrowhead=2, arrowsize=1, arrowwidth=2,arrowcolor="#636363", ax=20,ay=-30,bordercolor="#c7c7c7",
            borderwidth=2,borderpad=4,bgcolor="#ff7f0e",opacity=0.8)
        
        if len(labels_s)>0:
            fig_service = ff.create_distplot(service, labels_s,histnorm="probability density",colors=list(PORTS_COLORS.values()),show_rug=False,show_curve=False)
        else:
            fig_service=go.Figure()
            fig_service.add_annotation(x=2,y=5,xref="x",yref="y",text="max=5",showarrow=True,
            font=dict(family="Courier New, monospace",size=16, color="#ffffff"),align="center",
            arrowhead=2, arrowsize=1, arrowwidth=2,arrowcolor="#636363", ax=20,ay=-30,bordercolor="#c7c7c7",
            borderwidth=2,borderpad=4,bgcolor="#ff7f0e",opacity=0.8)
        
        
        ###Service and Waiting Graphs Layout
        fig_waiting.update_layout(layout,yaxis=dict(zeroline=True,linecolor='white',title_text="Density"),
                                  xaxis=dict(title_text="Hours"),
                                  legend=dict(x=0.6),title_text="<b>Waiting Time</b>")
        fig_waiting.add_annotation(annotation_layout,text="*Results from inbuilt method by Fuentes, Sanchez-Galan and Diaz")
        fig_waiting.update_traces(marker_line_color='rgb(8,48,107)',
                                  marker_line_width=1.5, opacity=0.6)
        fig_service.update_layout(layout,yaxis=dict(zeroline=True,linecolor="white",title_text="Density"),
                                  xaxis=dict(title_text="Hours"),
                                  legend=dict(x=0.6),title_text="<b>Service Time</b>")
        fig_service.add_annotation(annotation_layout,text="*Results from inbuilt method by Fuentes, Sanchez-Galan and Diaz")
        fig_service.update_traces(marker_line_color='rgb(8,48,107)',
                                  marker_line_width=1.5, opacity=0.6)
        
        
        return fig_waiting,fig_service,draught_fig
        
def lake_draught(fr="01-01-2015",to="18-11-2020",*args):
    gatun_in=gatun.copy()
    date_from=pd.to_datetime(fr)
    date_to=pd.to_datetime(to)
    
    gatun_in=gatun_in[gatun_in.Date.between(date_from,date_to)]
    gatun_in=gatun_in.assign(day=gatun_in.Date.dt.day.astype(str)+"/"+gatun_in.Date.dt.month.astype(str)+"/"+gatun_in.Date.dt.year.astype(str))
    lake_fig=make_subplots(specs=[[{"secondary_y": True}]])
    lake_fig.add_trace(go.Scatter(
                name="Gatun Lake Depth",
                mode="lines",
                x=gatun_in.day,y=gatun_in.gatun_depth,
                line=dict(shape="spline", width=2,color="#6671FD")),secondary_y=True)
    
    lake_fig.add_trace(go.Scatter(
                name="Draught Change",
                mode="lines",
                x=gatun_in[gatun_in.Change.notnull()]["day"],y=gatun_in[gatun_in.Change.notnull()]["Change"],
                line=dict(shape="spline", width=2,color="#3ACC95"),
                marker=dict(symbol="diamond-open")),secondary_y=False)
    
    lake_fig.add_trace(go.Scatter(
                name="Max draught",
                mode="lines",
                x=gatun_in.day,y=gatun_in.Overall,
                line=dict(shape="spline", width=2,color="#F9A054")),secondary_y=False)
    
    ##Layout update  
    lake_fig.update_layout(layout,title_text="<b>Gatun Lake and Draught Restriction Relation</b>",
                           xaxis=dict(title_text="Date",nticks=6),
                           legend=dict(x=0.6,y=1))
    
    # Set y-axes titles
    lake_fig.update_yaxes(title_text="Max Draught (m)", secondary_y=False,showgrid=False,
                          range=[gatun_in.Overall.min()*0.99,gatun_in.Overall.max()*1.05])
    lake_fig.update_yaxes(title_text="Lake Depth (m)", secondary_y=True,gridcolor="rgba(178, 178, 178, 0.1)",
                          title_font_size=15,tickfont_size=14,
                          title_font_family="HelveticaNeue",tickfont_family="HelveticaNeue",
                          range=[gatun_in.gatun_depth.min()*0.99,gatun_in.gatun_depth.max()*1.05])
    lake_fig.add_annotation(annotation_layout,text="*Values sourced by the Panama Canal Authority Maritime Services Platform")
    return lake_fig
    
def emissions_map(ghg,res,fr="01-01-2018",to="30-08-2020",lat=None,lon=None,zoom=None,type_vessel=[],size=[]):
    
    emissions_in=em.copy()
    date_fr=pd.to_datetime(fr)
    date_to=pd.to_datetime(to)
    
    df_aggreg=sum_by_hexagon(emissions_in,res,pol,date_fr,date_to,vessel_type=type_vessel,gt=size)
    
    
    ##Update layout
    if lat is not None:
        layout_map["mapbox"]["center"]["lon"]=lon
        layout_map["mapbox"]["center"]["lat"]=lat
        layout_map["mapbox"]["zoom"]=zoom
        
    if df_aggreg.shape[0]>0:
        heatmap=choropleth_map(ghg,df_aggreg,layout_map)
    else:
        heatmap=go.Figure(data=go.Scattermapbox(lat=[0],lon=[0]),layout=layout_map)

    return heatmap

##Upper Row,
@app.callback(
    [
        Output("waitingText", "children"),
        Output("opsText", "children"),
        Output("serviceText", "children"),
        Output("date_from","children"),
        Output("date_to","children"),
        Output("size_from","children"),
        Output("size_to","children"),
    ],
    [Input("ports-dropdown", "value"),
     Input("types-dropdown","value"),
     Input('year_slider', 'value'),
     Input('size_slider', 'value'),
     ],
)
def update_row1(ports_val,types_val,date,size_val):
    if not ports_val:
        ports_val=["All"]
    if not types_val:
        types_val=["All"]
    
    date_fr=pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[0])
    date_to=pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[1])
    date_to=date_to+ relativedelta(day=31)  
    
    if date[0]==0:
        date_fr=pd.to_datetime("31-12-2018")    
    
    date_fr=date_fr.strftime('%d-%m-%Y')
    date_to=date_to.strftime('%d-%m-%Y')
    
    waiting,ops,service=upper_text_p1(fr=date_fr,to=date_to,ports_sel=ports_val,type_vessel=types_val,size=size_val)
    
    return "{:.1f}".format(waiting)+ " hours", format(ops,","), "{:.1f}".format(service) + " hours",\
        date_fr, date_to ,format(size_val[0],","),format(size_val[1],",")
    

@app.callback(
    [
        Output("service_graph", "figure"),
        Output("waiting_graph", "figure"),
        Output("ratio_graph", "figure"),

    ],
    [Input("ports-dropdown", "value"),
      Input("types-dropdown","value"),
      Input('year_slider', 'value'),
      Input('size_slider', 'value'),
      ],
)


def update_graphs(ports_val,types_val,date,size_val):
    if not ports_val:
        ports_val=["All"]
    if not types_val:
        types_val=["All"]
  
    date_fr=pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[0])
    date_to=pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[1])
    date_to=date_to+ relativedelta(day=31)  
    
    if date[0]==0:
        date_fr=pd.to_datetime("31-12-2018")    
    
    date_fr=date_fr.strftime('%d-%m-%Y')
    date_to=date_to.strftime('%d-%m-%Y')
    
    service_g,waiting_g,ratio_g=upper_text_p1(fr=date_fr,to=date_to,ports_sel=ports_val,type_vessel=types_val,size=size_val,text_bar=False)
    
    return service_g,waiting_g,ratio_g

@app.callback(
    Output("draught_graph", "figure"),
    [ Input('year_slider', 'value'),
      ],
)

def update_gatun(date):

    date_fr=pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[0])
    date_to=pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[1])
    date_to=date_to+ relativedelta(day=31)  
    
    if date[0]==0:
        date_fr="30-12-2018"
    
    if date[1]==20:
        date_to="18-11-2020"
        
    lake_g=lake_draught(fr=date_fr,to=date_to)
    
    return lake_g

@app.callback(
    Output("map_in", "figure"),
    [Input("selector","value"),
     Input("zoom_slider","value"),
     Input('year_slider', 'value'),
     Input("types-dropdown","value"),
      ],
    [State("map_in","relayoutData")]
)

def update_emissions_map(ghg_t,resol,date,types_val,relay):
    
    date_fr=pd.to_datetime("01-01-2019 00:00")+relativedelta(months=+date[0])
    date_to=pd.to_datetime("01-01-2019 00:00")+relativedelta(months=+date[1])
    date_to=date_to+ relativedelta(day=31)
    
    if relay is not None:   
        if "mapbox.center" in relay.keys():
            lat=relay["mapbox.center"]["lat"]
            lon=relay["mapbox.center"]["lon"]
            zoom=relay["mapbox.zoom"]
        else:
            lat=8.93
            lon=-79.55
            zoom=9
    else:
        lat=8.93
        lon=-79.55
        zoom=9
    
    if "All" in types_val:
        types_val=[]
    
    ####Size deactived for the time being.
    emission_fig=emissions_map(ghg_t,resol,fr=date_fr,to=date_to,lat=lat,lon=lon,zoom=zoom,type_vessel=types_val,size=[])
        
    return emission_fig 

###Month and type update on map
@app.callback(
     Output("month_map", "children"),
    [ Input('year_slider', 'value'),
      ],
)

def month_map(date):
    fr=(pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[0]))
    to=(pd.to_datetime("12-01-2018 00:00")+relativedelta(months=+date[1]))
    
    m_fr=datetime.strptime(str(fr.month), "%m").strftime("%b")
    m_to=datetime.strptime(str(to.month), "%m").strftime("%b")

    
    m_e="{} {} to {} {}".format(m_fr,fr.year,m_to,to.year)
    
    return m_e
    
##Refresh button
@app.callback([Output("ports-dropdown", "value"),
               Output("types-dropdown","value"),
               Output('year_slider', 'value'),
               Output('size_slider', 'value')],
              [Input('refresh-button', 'n_clicks')])     

def clearMap(n_clicks):
    if n_clicks !=0:
        pdd=["All"]
        tdd=["All"]
        ysld=[0,20]
        ssld=[400,170000]
        return pdd,tdd,ysld,ssld
    
if __name__ == "__main__":
    app.run_server(debug=True,use_reloader=False)

