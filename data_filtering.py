# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 10:24:39 2020

@author: gabri
"""

import pandas as pd
import numpy as np

def processed_data():
    ##Ports info adjust and filtering.
    df=pd.read_csv("data/ports_solutions_sp.csv")
    
    ##Less than 30 mins as this is the minimum number of positions to have a. Then kalman didnt work. Fix kalman to avoid this.
    ##Some didnt go thorugh kalman and have a faulty reading.
    df["waiting_time"]=np.where(df.waiting_time<0.5,np.nan,df.waiting_time)
    df["waiting_time"]=np.where(df.waiting_time>150,150,df.waiting_time)
    
    
    ##Remove potential bunkering ops, Non in Telfer. 
    ###There is no oil operations inside Canal other than bunkering supplied.
    ###Need to refine to identify bunkering in Patsa from loading ops
    df=df[~(df["Fleet Type"]=="Product Tankers")&(df["port_name"]!="Telfer")]
    
    ##Containers not in PATSA in PSA and Types adjustments
    df["Fleet Type"]=np.where(df.vessel_type_main=="Container Ship","Containerships",df["Fleet Type"])
    df["Fleet Type"]=np.where(df["Fleet Type"]=="PCC","Ro-Ro",df["Fleet Type"])
    df["port_name"]=np.where(df["Fleet Type"]=="Containerships",np.where(df["port_name"]=="Pacific - PATSA",
                              "Pacific - PSA",df["port_name"]),df["port_name"])
    
    ##Nan replacements when possible
    df["Fleet Type"]=np.where(df["Fleet Type"].isnull(),
                              np.where(df.vessel_type_main!="None",df.vessel_type_main,df["Fleet Type"]),
                                        df["Fleet Type"])
    
    ##Types fix
    
    df["Fleet Type"]=np.where(df["Fleet Type"].isin(["Offshore","Offshore Support Vessel"]),"Offshore Vessel",df["Fleet Type"])
    
    df["Fleet Type"]=np.where(df["Fleet Type"].isin(["MPP","General Cargo Ship"]),"General Cargo",df["Fleet Type"])
    
    df["Fleet Type"]=np.where(df["Fleet Type"].isin(["Oil And Chemical Tanker","Chemical Tankers"]),"Other Tanker",df["Fleet Type"])
    
    df["Fleet Type"]=np.where(df["Fleet Type"].isin(["Cruise"]),"Passenger Ship",df["Fleet Type"])
    
    df["Fleet Type"]=np.where(df["Fleet Type"].isin(["Bulkers"]),"Bulk Carrier",df["Fleet Type"])
    
    df["Fleet Type"]=np.where(df["Fleet Type"].isin(["Fishing Vessel","Pleasure Craft","Service Ship","Cable Layer"]),
                              "Others",df["Fleet Type"])
    
    df=df[df["Fleet Type"].notnull()]
    
    ###As I dont recognize the servicing vessel, I will just keep containers, ro-ro and passagner. FOR THE MOMENT
    
    df=df[df["Fleet Type"].isin(["Containerships","Ro-Ro","Passenger Ship"])]
    
    ##Quantiles on service and waiting times to remove outliers. 10% winzorization
    ##Direct visit from after lockage.
    grouped_df=df.groupby("port_name")
    df=grouped_df.apply(lambda x: x[(x.waiting_time.isnull())|((x["service_time"]>=x["service_time"].quantile(0.05))&
                                    (x["service_time"]<=x["service_time"].quantile(0.95))&
                                    (x["waiting_time"]>=x["waiting_time"].quantile(0.05))&
                                    (x["waiting_time"]<=x["waiting_time"].quantile(0.95))&
                                    (x.waiting_time.notnull()))]).reset_index(drop=True)
    waiting=df.groupby("port_name").waiting_time.describe()
    
    service=df.groupby("port_name").service_time.describe()
    
    ###Panama Info. Next time, rescue types from AIS reading
    
    canal=pd.read_csv("data/panama_transits_sp.csv")
    canal=canal[canal["Fleet Type"].notnull()]
    
    
    ##Errors in values
    return canal,df



