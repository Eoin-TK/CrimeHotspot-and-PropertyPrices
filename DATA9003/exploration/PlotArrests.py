import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import folium as fl
from folium import plugins
from importlib import resources
import branca.colormap as cm

from DATA9003 import assets


# OBJECT TYPE: Function
# RETURN TYPE: MatPlotLib Axes
# NAME:  AnnualArrests
# DESCRIPTION:  Generate a pivot table showing the number of arrests annually in each borough for all years and plot the results in the form of a bar chart

def AnnualArrests(arrests_df, FigDir=None):

    mydf = arrests_df[["year", "arrest_boro"]]
    mydf.columns = ["Year", "Borough"]

    # make pivot table
    MyTable = pd.pivot_table(mydf,
                             index="Year",
                             columns="Borough",
                             aggfunc=len)

    # plot pivot table
    ax = MyTable.plot(kind="bar",
                      figsize=(12, 8),
                      fontsize=16)

    # add title
    ax.set_title("Annual Arrests by Borough",
                 fontsize=25)

    # save plot in FigDir if specified
    if FigDir is not None:
        imgpath = os.path.join(FigDir, "AnnualArrests.png")
        plt.savefig(imgpath)

    return ax


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame (Pivot Table) + Plot (saved as jpeg)
# NAME:  OfnsTypeByBorough
# DESCRIPTION:  Generate a pivot table showing the number of arrests for different offence types in each borough and plot the results in the form of a bar chart

def OfnsTypeByBorough(arrests_df, FigDir=None, yr=None):

    # filter df if necessary
    if yr is None:
        mydf = arrests_df[["arrest_boro", "ofns_type"]]
        title = "Arrests for Different Offences by Borough"
    else:
        mydf = arrests_df.loc[arrests_df["year"] == yr][["arrest_boro", "ofns_type"]]
        title = "Arrests for Different Offences in {} by Borough".format(yr)

    mydf.columns = ["Borough", "Offence Type"]

    # generate pivot table from df
    pivottable = pd.pivot_table(mydf,
                                index="Offence Type",
                                columns="Borough",
                                aggfunc=len)

    # plot pivot table
    ax = pivottable.plot(kind="bar",
                         figsize=(12, 8),
                         fontsize=16)
    ax.tick_params(axis='x', labelrotation=15)
    ax.set_xlabel("")

    # add title
    ax.set_title(title,
                 fontsize=25)

    if FigDir is not None:
        imgpath = os.path.join(FigDir, "OffenceTypeByBorough.jpg")
        plt.savefig(imgpath)

    return ax


# OBJECT TYPE: Function
# RETURN TYPE: MatPlotLib Axes
# NAME:  OfnsDescByBorough
# DESCRIPTION:  Generate a pivot table showing the breakdown of arrests for a specific type of offence in each borough and plot the results in the form of a bar chart

def OfnsDescByBorough(arrests_df, ofns_type, FigDir=None, yr=None):

    # filter df if necessary
    if yr is None:
        mydf = arrests_df.loc[arrests_df["ofns_type"] == ofns_type][["arrest_boro", "ofns_desc"]]
        title = "Arrests for {}".format(ofns_type)
    else:
        mydf = arrests_df.loc[(arrests_df["year"] == yr) & (arrests_df["ofns_type"] == ofns_type)][["arrest_boro", "ofns_desc"]]
        title = "Arrests for {} in {}".format(ofns_type, yr)

    mydf.columns = ["Borough", "Offence Description"]

    # create pivot table from df
    pivottable = pd.pivot_table(mydf,
                                index="Offence Description",
                                columns="Borough",
                                aggfunc=len)

    # plot pivot table
    ax = pivottable.plot(kind="bar",
                         figsize=(12, 8),
                         fontsize=16)
    ax.tick_params(axis='x', labelrotation=0)
    ax.set_xlabel("")

    # add title
    ax.set_title(title,
                 fontsize=25)

    if FigDir is not None:
        imgpath = os.path.join(FigDir, "OffenceDescByBorough.jpg")
        plt.savefig(imgpath)

    return ax


# OBJECT TYPE: Function
# RETURN TYPE: Folium Map
# NAME:  HeatMap_Static
# DESCRIPTION:  Plot a folium (leaflet) heatmap of arrest data

def HeatMap_Static(arrests_df, ofns_type=None, ofns_desc=None):
    # apply filters if necessary
    if ofns_type is None:
        mydf = arrests_df
        minopac = 0.01
    elif ofns_desc is None:
        mydf = arrests_df.loc[(arrests_df["ofns_type"] == ofns_type)]
        minopac = 0.1
    else:
        mydf = arrests_df.loc[(arrests_df["ofns_type"] == ofns_type) & (arrests_df["ofns_desc"] == ofns_desc)]
        minopac = 0.1

    # count the number of arrests at each location
    mydf = mydf.groupby(["latitude", "longitude"]).agg({"arrest_key": "count"})
    mydf.reset_index(inplace=True)

    # normalise count value
    mydf.arrest_key = mydf.arrest_key / max(mydf.arrest_key)

    # subway lines data
    with resources.path("DATA9003.assets", "SubwayLines.geojson") as geofile:
        sbwy = gpd.read_file(geofile)

    lines = fl.features.GeoJson(sbwy.geometry,
                                style_function=lambda x: {'color': '#a1a1a1',
                                                          'weight': 1})

    # convert from pandas df to geopandas GeoDataFrame
    geodf = gpd.GeoDataFrame(mydf,
                             geometry=gpd.points_from_xy(mydf.longitude, mydf.latitude))

    # set coord ref system (crs)
    geodf.set_crs(epsg=4326, inplace=True)

    # leaflet map of NYC
    mymap = fl.Map(location=[40.730610, -73.935242], tiles="Cartodb dark_matter", zoom_start=10)

    # add subway lines to map
    mymap.add_child(lines)

    # heatmap overlay
    heatdata = [[point.xy[1][0], point.xy[0][0], wgt] for point, wgt in zip(geodf.geometry, geodf.arrest_key)]
    plugins.HeatMap(heatdata, radius=20, min_opacity=minopac).add_to(mymap)

    htmlout="StaticHeatMap.html"
    mymap.save(htmlout)

    return mymap


# OBJECT TYPE: Function
# RETURN TYPE: Folium Map
# NAME:  HeatMap_Dynamic
# DESCRIPTION:  Plot an animated folium (leaflet) heatmap of arrest data

def HeatMap_Dynamic(arrests_df, ofns_type=None, ofns_desc=None, timestep="month", FigDir=None):
    # apply filters if necessary
    if ofns_type is None:
        mydf = arrests_df
    elif ofns_desc is None:
        mydf = arrests_df.loc[(arrests_df["ofns_type"] == ofns_type)]
    else:
        mydf = arrests_df.loc[(arrests_df["ofns_type"] == ofns_type) & (arrests_df["ofns_desc"] == ofns_desc)]

    # count the number of arrests at each location at each point in time
    mydf = mydf.groupby(["year", timestep, "latitude", "longitude"]).agg({"arrest_key": "count"})
    mydf.reset_index(inplace=True)

    # normalise count values
    mydf.arrest_key = mydf.arrest_key / max(mydf.arrest_key)

    # subway lines data
    with resources.path("DATA9003.assets", "SubwayLines.geojson") as geofile:
        sbwy = gpd.read_file(geofile)

    lines = fl.features.GeoJson(sbwy.geometry,
                                style_function=lambda x: {'color': '#a1a1a1',
                                                          'weight': 1.5})

    # convert from pandas df to geopandas GeoDataFrame
    geodf = gpd.GeoDataFrame(mydf,
                             geometry=gpd.points_from_xy(mydf.longitude, mydf.latitude))

    # set coord ref system (crs)
    geodf.set_crs(epsg=4326, inplace=True)

    # leaflet map of NYC
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="Cartodb dark_matter",
                   zoom_start=10)

    # add subway lines to map
    mymap.add_child(lines)

    # heatmap overlay
    timedata = [t for t in geodf[timestep].unique()]
    heatdata = []
    for t in timedata:
        # foliums HeatMapWithTime requires data in a specific format
        # get lat long and relative weight of each street segment at time t
        heat_df = geodf.loc[(geodf[timestep] == t)]
        heatdata.append(
            [[point.xy[1][0], point.xy[0][0], wgt] for point, wgt in zip(heat_df.geometry, heat_df.arrest_key)])

    plugins.HeatMapWithTime(data=heatdata,
                            index=timedata,
                            min_opacity=0.2).add_to(mymap)

    if FigDir is not None:
        htmlout = os.path.join(FigDir, "DynamicHeatMap.html")
        mymap.save(htmlout)

    return mymap


# OBJECT TYPE: Function
# RETURN TYPE: Folium Map
# NAME:  CrimeChoropleth
# DESCRIPTION:  Plot a choropleth showing number of arrests by zipcode

def CrimeChoropleth(arrests_df, yr=None, FigDir=None):

    # filter data for relevant year if specified
    if yr is not None:
        mydf = arrests_df.loc[arrests_df.year == yr]
    else:
        mydf = arrests_df

    # count the number of arrests in each tract
    mydf = mydf.groupby(["OBJECTID"]).agg(count=("arrest_key", "count"))

    # leaflet map of NYC
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="Cartodb positron",
                   zoom_start=10)

    # read in GIS data for census tracts
    with resources.path(assets, "censustracts.geojson") as myfile:
        census = gpd.read_file(myfile)
        census["OBJECTID"] = census["OBJECTID"].astype(int)
        census = census[["OBJECTID", "geometry"]]
        census.to_crs(epsg=4326, inplace=True)

    # match counts with GIS data of relevant tract
    tractdf = gpd.GeoDataFrame(mydf.merge(census,
                                          on="OBJECTID",
                                          how="inner"))

    # specify a continuous colour map for the choropleth
    cmap = cm.LinearColormap(['white', 'yellow', 'orange', 'red'],
                               vmin=tractdf["count"].min(),
                               vmax=tractdf["count"].max())
    cmap.caption="Number of Arrests"

    # specify the style for the census tracts
    style_func = lambda x: {'weight': 0.5,
                            'color':'black',
                            'fillColor': cmap(x['properties']['count']),
                            'fillOpacity': 0.75}

    # specify highlight style to indicate the tract being hovered on
    hili_func = lambda x: {'fillColor': '#000000',
                            'color':'#000000',
                            'fillOpacity': 0.5,
                            'weight': 0.1}

    # style details for popups that appear on hover for each tract
    popup_style = ("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")

    # create the choropleth layer
    choro = fl.features.GeoJson(tractdf,
                                style_function=style_func,
                                highlight_function=hili_func,
                                control=False,
                                tooltip=fl.features.GeoJsonTooltip(fields=['OBJECTID', 'count'],
                                                                   aliases=['Tract ID', 'Number of Arrests'],
                                                                   style=popup_style,
                                                                   sticky=True))

    # add the choropleth and colormap to the base map
    choro.add_to(mymap)
    cmap.add_to(mymap)

    # save leaflet map as html file
    if FigDir is not None:
        htmlout = os.path.join(FigDir, "CrimeChoro.html")
        mymap.save(htmlout)

    return mymap
