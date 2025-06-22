import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium as fl
from importlib import resources
import geopandas as gpd
import seaborn as sns
import branca.colormap as cm

from DATA9003 import assets

# OBJECT TYPE: Function
# RETURN TYPE: Pandas PivotTable
# NAME:  AnnualSales
# DESCRIPTION:  Generate a pivot table showing the number of sales annually in each borough for all years and plot the results in the form of a bar chart

def AnnualSales(sales_df, FigDir=None):

    # make pivot table
    MyTable = pd.pivot_table(sales_df[["year", "borough"]],
                             index="year",
                             columns="borough",
                             aggfunc=len)

    # plot pivot table
    ax = MyTable.plot(kind="bar",
                      figsize=(12, 6),
                      fontsize=16,
                      legend=False)

    # add legend
    lgnd = ax.legend(MyTable.columns,
              bbox_to_anchor=(1.02, 1.0),
              fontsize = 12,
              title_fontsize=12,
              title="Borough",
              loc="upper left")

    # add title
    ax.set_title("Annual Home Sales by Borough",
                 fontsize=25)

    # save in directory if specified
    if FigDir is not None:
        filepath = os.path.join(FigDir, "AnnualSales.png")
        plt.savefig(filepath, bbox_extra_artists=(lgnd,), bbox_inches='tight')

    return MyTable


# OBJECT TYPE: Function
# RETURN TYPE: Pandas PivotTable
# NAME:  AvgPriceOverTime
# DESCRIPTION:  Generate a pivot table showing the median sale price for each year and plot the results in the form of a line chart

def AvgPriceOverTime(sales_df, FigDir=None):

    # make pivot table
    MyTable = pd.pivot_table(sales_df[["borough", "year", "sale_price"]],
                             index="year",
                             columns="borough",
                             aggfunc={"sale_price": np.median})

    # plot pivot table
    ax = MyTable.plot(kind="line",
                      figsize=(12, 8),
                      fontsize=16,
                      legend=False)

    # add legend & title
    lgnd = ax.legend(MyTable.columns.get_level_values(1),
              bbox_to_anchor=(1.02, 1.0),
              fontsize=12,
              title_fontsize=12,
              title="Borough",
              loc="upper left")

    ax.set_title("Median Property Price",
                 fontsize=25)

    if FigDir is not None:
        filepath = os.path.join(FigDir, "AvgPriceOverTime.png")
        plt.savefig(filepath, bbox_extra_artists=(lgnd,), bbox_inches='tight')

    return MyTable


# OBJECT TYPE: Function
# RETURN TYPE: Pandas PivotTable
# NAME:  PriceViolin
# DESCRIPTION:  Generate a violin plot showing the distribution of sale prices for both property types in each borough

def PriceViolin(sales_df, FigDir=None):
    fig, ax = plt.subplots(figsize=(6, 10))

    sns.violinplot(y=sales_df.borough,
                   x=sales_df.sale_price,
                   ax=ax)

    ax.set_xlabel("Sale Price")
    ax.set_ylabel("Borough")
    ax.set_title("Distribution of Property Prices")

    if FigDir is not None:
        filepath = os.path.join(FigDir, "PriceViolin.jpg")
        plt.savefig(filepath)

    return fig


# OBJECT TYPE: Function
# RETURN TYPE: folium map
# NAME:  SalesChoropleth
# DESCRIPTION:  Generate a pivot table showing the median sale price for each year and plot the results in the form of a line chart

def SalesChoropleth(sales_df, yr, FigDir=None):

    # get median sale price in each zipcode
    mydf = sales_df.loc[(sales_df.year == yr)].groupby(["zipcode"]).agg(Median=("sale_price", np.median))
    mydf.reset_index()

    # read in GIS data for zipcodes
    with resources.path(assets, "zipcodes.zip") as zipfile:
        zipcodes = gpd.read_file(zipfile)
        zipcodes.columns = [name.lower() for name in zipcodes.columns]
        zipcodes["zipcode"] = zipcodes.zipcode.astype(int)
        zipcodes = zipcodes[["zipcode", "geometry"]]
        zipcodes.to_crs(epsg=4326, inplace=True)

    # match property coords to zipcodes
    finaldf = gpd.GeoDataFrame(mydf.merge(zipcodes,
                                          on="zipcode",
                                          how="inner"))

    # leaflet map of NYC
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="Cartodb positron",
                   zoom_start=10)

    # make linear colour map
    colmap = cm.LinearColormap(['red', 'yellow', 'green'],
                               vmin=finaldf.Median.min(),
                               vmax=finaldf.Median.max())
    colmap.caption="Median Sale Price ($)"

    # style function for zipcodes
    style_func = lambda x: {'weight': 0.5,
                            'color':'black',
                            'fillColor': colmap(x['properties']['Median']),
                            'fillOpacity': 0.75}

    # highlight function for the zipcode being hovered on
    hili_func = lambda x: {'fillColor': '#000000',
                            'color':'#000000',
                            'fillOpacity': 0.5,
                            'weight': 0.1}

    # style for popups
    popup_style = ("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")

    # make choropleth
    choro = fl.features.GeoJson(data=finaldf,
                                style_function=style_func,
                                highlight_function=hili_func,
                                control=False,
                                tooltip=fl.features.GeoJsonTooltip(fields=['zipcode', 'Median'],
                                                                   aliases=['Zipcode', 'Median Sale Prices'],
                                                                   style=popup_style,
                                                                   sticky=True))

    # add choropleth to map
    mymap.add_child(choro)
    colmap.add_to(mymap)

    if FigDir is not None:
        htmlout = os.path.join(FigDir, "PriceChoro.html")
        mymap.save(htmlout)

    return mymap
