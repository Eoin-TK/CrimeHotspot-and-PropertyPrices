# IMPORT REQUIRED PACKAGES
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import geopandas as gpd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import ArcGIS
import os
import numpy as np
import ast
from importlib import resources
from DATA9003 import assets


# OBJECT TYPE: Function
# RETURN TYPE: Boolean
# NAME:  OffBy
# DESCRIPTION:  Check if a given value is within range of some target value

def OffBy(value, target, within = 0.002):
    # get bounds
    lwr = target - within
    upr = target + within

    # test value
    if lwr <= value <= upr:
        return True
    else:
        return False


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  GetTable
# DESCRIPTION:  Scrape a table of addresses for NYPD precinct houses (https://www1.nyc.gov/site/nypd/bureaus/patrol/precincts-landing.page)

def GetTable():
    url = "https://www1.nyc.gov/site/nypd/bureaus/patrol/precincts-landing.page"

    # SCRAPE WEBSITE
    webpage = requests.get(url)
    soup = BeautifulSoup(webpage.text, 'lxml')

    # EXTRACT DATA

    # pull table
    links = soup.select("table tbody tr")

    # prep empty DataFrame
    myDF = pd.DataFrame(columns=["Precinct", "Phone No", "Address", "Borough"])

    # fill dataframe
    for i in links:
        # entries are listed under different subheadings for different boroughs
        if i.find("th") is not None:
            borodata = i.find("th")
            boro = borodata.text

        # row data is listed in cells
        row_data = i.find_all("td")
        row = [j.text for j in row_data]
        length = len(myDF)

        # add row to end of dataframe
        if len(row) > 0:
            row.append(boro)
            myDF.loc[length] = row

    # drop phone no. column
    myDF = myDF.drop(["Phone No"], axis=1)

    # add borough, state & country to address for geocoding
    myDF["Address"] = myDF["Address"] + ", " + myDF["Borough"] + ", NY, US"

    # drop borough column now that the data is added to the address
    myDF = myDF.drop(["Borough"], axis=1)

    return myDF


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  GetCoords
# DESCRIPTION:  Expand the list of station houses with other locations identified during data exploration & geocode

def GetStationCoords(mydir):
    filepath=os.path.join(mydir, "NYPD_stations.csv")

    if os.path.exists(filepath):
        myDF = pd.read_csv(filepath)
        myDF.point = myDF.point.apply(ast.literal_eval)
    else:
        myDF = GetTable()

        # expand list with locations identified during data exploration:

        # NYPD Manhattan Central Booking
        ManhattanCB = {"Precinct": "Central Booking (Manhattan)",
                       "Address": "100 Centre Street, Manhattan, NY, US"}
        myDF = myDF.append(ManhattanCB, ignore_index=True)

        # NYPD Bronx Central Booking
        BronxCB = {"Precinct": "Central Booking (Bronx)",
                   "Address": "215 East 161 Street, The Bronx, NY, US"}
        myDF = myDF.append(BronxCB, ignore_index=True)

        # Bronx Detective Bureau
        DBBX = {"Precinct": "Bronx Detective Bureau",
                "Address": "1086 Simpson Street, The Bronx, NY, United States"}
        myDF = myDF.append(DBBX, ignore_index=True)

        # Vernon C. Bain Correction Centre
        PrisonShip = {"Precinct": "Vernon C. Bain Correction Centre",
                      "Address": "1 Halleck Street, The Bronx, NY, US"}
        myDF = myDF.append(PrisonShip, ignore_index=True)

        # Times Square Substation
        TimesSquare = {"Precinct": "Time Square Substation",
                       "Address": "1479 Broadway, Manhattan, NY, US"}
        myDF = myDF.append(TimesSquare, ignore_index=True)

        # Police Service Area 1
        SA_1 = {"Precinct": "Service Area 1",
                "Address": "2860 West 23 Street, Brooklyn, NY, US"}
        myDF = myDF.append(SA_1, ignore_index=True)

        # Police Service Area 2
        SA_2 = {"Precinct": "Service Area 2",
                "Address": "560 Sutter Avenue, Brooklyn, NY, US"}
        myDF = myDF.append(SA_2, ignore_index=True)

        # Police Service Area 3
        SA_3 = {"Precinct": "Service Area 3",
                "Address": "25 Central Avenue, Brooklyn, NY, US"}
        myDF = myDF.append(SA_3, ignore_index=True)

        # Police Service Area 4
        SA_4 = {"Precinct": "Service Area 4",
                "Address": "130 Avenue C, Manhattan, NY, US"}
        myDF = myDF.append(SA_4, ignore_index=True)

        # Police Service Area 5
        SA_5 = {"Precinct": "Service Area 5",
                "Address": "221 East 123rd Street, Manhattan, NY, US"}
        myDF = myDF.append(SA_5, ignore_index=True)

        # Police Service Area 6
        SA_6 = {"Precinct": "Service Area 6",
                "Address": "2770 Frederick Douglass Boulevard, Manhattan, NY, US"}
        myDF = myDF.append(SA_6, ignore_index=True)

        # Police Service Area 7
        SA_7 = {"Precinct": "Service Area 7",
                "Address": "737 Melrose Avenue, The Bronx, NY, US"}
        myDF = myDF.append(SA_7, ignore_index=True)

        # Police Service Area 8
        SA_8 = {"Precinct": "Service Area 8",
                "Address": "2794 Randall Avenue, The Bronx, NY, US"}
        myDF = myDF.append(SA_8, ignore_index=True)

        # Police Service Area 9
        SA_9 = {"Precinct": "Service Area 9",
                "Address": "155-09 Jewel Avenue, Queens, NY, US"}
        myDF = myDF.append(SA_9, ignore_index=True)

        # geocode addresses
        locator = ArcGIS(user_agent="nypdprecinct")

        # 1 - incorporate delay between geocoding calls (avoid usage limits)
        geocode = RateLimiter(locator.geocode, min_delay_seconds=0.1)

        # 2- - create location column
        myDF['location'] = myDF['Address'].apply(geocode)

        # 3 - get long, lat and alt from location column (returns tuple)
        myDF['point'] = myDF['location'].apply(lambda loc: tuple(loc.point) if loc else None)

        # save to file to avoid having to repeat geocoding
        myDF.to_csv(filepath, index=False)

    return myDF


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  LoadArrestsData
# DESCRIPTION:  Load and clean the NYPD arrests dataset

def LoadArrestsData(CrimeDir, SourceFile, NewFile):
    filepath = os.path.join(CrimeDir, NewFile)

    if os.path.exists(filepath):
        arrests_df = pd.read_csv(filepath)

    else:

        # columns to use
        cols = ["ARREST_KEY",
                "ARREST_DATE",
                "LAW_CODE",
                "ARREST_BORO",
                "PERP_RACE",
                "Latitude",
                "Longitude"]

        # read file
        arrests_df = pd.read_csv(os.path.join(CrimeDir, SourceFile),
                                 usecols=cols)

        arrests_df.dropna(inplace=True)

        # make column names lowercase
        arrests_df.columns = [name.lower() for name in cols]

        # change columns to appropriate type
        arrests_df["law_code"] = arrests_df["law_code"].astype("string")
        arrests_df['arrest_date'] = pd.to_datetime(arrests_df["arrest_date"], format="%m/%d/%Y")

        # filter for violations of Penal Law only
        arrests_df = arrests_df.loc[arrests_df["law_code"].str.startswith("PL ")]

        # extract year from date
        arrests_df["year"] = arrests_df["arrest_date"].dt.year
        arrests_df = arrests_df.loc[arrests_df.year < 2021]

        # extract quarter from date
        arrests_df["quarter"] = arrests_df["arrest_date"].dt.quarter
        arrests_df["quarter"] = "Q" + arrests_df["quarter"].astype(str) + "-" + arrests_df["year"].astype(str)

        # extract month from date
        arrests_df["month"] = arrests_df["arrest_date"].dt.month
        arrests_df["month"] = arrests_df["month"].astype(str) + "/" + arrests_df["year"].astype(str)

        # Extract article number from law code
        arrests_df["law_code"] = arrests_df["law_code"].str.replace("PL ", "")
        arrests_df["article"] = arrests_df["law_code"].str.slice(0, 3).astype(int)
        arrests_df.drop(["law_code"], axis=1, inplace=True)

        arrests_df["ofns_type"] = "-"
        arrests_df["ofns_desc"] = "-"

        # read in article numbers
        with resources.open_text(assets, "ArticleNumbers.json") as jsonfile:
            lawdict = json.load(jsonfile)

        # classify offense type and description using article numbers
        for ofns_type in lawdict.keys():

            key_min = min(lawdict[ofns_type], key=lawdict[ofns_type].get)
            key_max = max(lawdict[ofns_type], key=lawdict[ofns_type].get)

            cond1a = lawdict[ofns_type][key_min] <= arrests_df["article"]
            cond1b = arrests_df["article"] <= lawdict[ofns_type][key_max]

            arrests_df.loc[(cond1a) & (cond1b), "ofns_type"] = ofns_type

            for ofns_desc in lawdict[ofns_type].keys():
                cond2 = arrests_df["article"] == lawdict[ofns_type][ofns_desc]
                arrests_df.loc[cond2, "ofns_desc"] = ofns_desc

        # remove article number - no longer required
        arrests_df.drop(["article"], axis=1, inplace=True)

        # exploration revealed some offence types seldom occur => treat as removable outliers
        out1 = arrests_df["ofns_type"] != "Anticipatory"
        out2 = arrests_df["ofns_type"] != "Family/Child Welfare"
        out3 = arrests_df["ofns_type"] != "Firearms/Fireworks/Pornography/Gambling"
        out4 = arrests_df["ofns_type"] != "Fraud"
        out5 = arrests_df["ofns_type"] != "Organised Crime"
        out6 = arrests_df["ofns_type"] != "Terrorism"

        arrests_df = arrests_df.loc[(out1) & (out2) & (out3) & (out4) & (out5) & (out6)]

        # filter out arrests made at police stations

        # read in locations of stations
        precincts = GetStationCoords(CrimeDir)

        # if an arrest was made near one of these location change coords to (0,0)
        for station in precincts.point:
            cond_A = arrests_df["latitude"].apply(OffBy, args=[station[0]])
            cond_B = arrests_df["longitude"].apply(OffBy, args=[station[1]])

            arrests_df.loc[(cond_A) & (cond_B), "latitude"] = 0
            arrests_df.loc[(cond_A) & (cond_B), "longitude"] = 0

        # treat coord 0 as NaN + remove
        arrests_df["latitude"].replace(0, np.nan, inplace=True)
        arrests_df["longitude"].replace(0, np.nan, inplace=True)

        # use coords to match arrests to zipcode
        arrests_df = gpd.GeoDataFrame(arrests_df,
                                      geometry=gpd.points_from_xy(arrests_df.longitude, arrests_df.latitude))

        # set coord reference system to EPSG:4326
        arrests_df.set_crs(epsg=4326, inplace=True)

        # read in GIS data for zipcodes
        with resources.path(assets, "zipcodes.zip") as zipfile:
            zipcodes = gpd.read_file(zipfile)
            zipcodes.columns = [name.lower() for name in zipcodes.columns]
            zipcodes = zipcodes[["zipcode", "geometry"]]
            zipcodes.to_crs(epsg=4326, inplace=True)

        # match arrest coords to zipcodes
        arrests_df = gpd.sjoin(arrests_df,
                               zipcodes,
                               how="left",
                               op="within")

        arrests_df.dropna(inplace=True)
        arrests_df.drop(["index_right"],
                        axis=1,
                        inplace=True)

        # read in census tract GIS data
        with resources.path("DATA9003.assets", "censustracts.geojson") as censusfile:
            census = gpd.read_file(censusfile)
            census = census[["OBJECTID", "geometry"]]
            census.to_crs(epsg=4326, inplace=True)

        # match arrest coords to census tract
        arrests_df = gpd.sjoin(arrests_df,
                               census,
                               how="left",
                               op="within")

        arrests_df.dropna(inplace=True)
        arrests_df.drop(["geometry", "index_right"],
                        axis=1,
                        inplace=True)

        # sort arrests by date
        arrests_df.sort_values("arrest_date",
                               inplace=True,
                               ignore_index=True)

        # write to file to avoid having to repeat cleaning operations
        arrests_df.to_csv(filepath, index=False)

    print(arrests_df.info())
    return arrests_df


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME: HoutSpots_micro
#DESCRIPTION: Determine the micro-geographic concentration of arrests

def HotSpots_micro(arrests_df, threshold, output=False):
    # count total arrests
    arrestscount = len(arrests_df)

    # count arrests at each street segments
    locationtotals = arrests_df.groupby(["latitude", "longitude"]).agg({"arrest_key": "count"})

    # sort street segments by arrest count and calculate arrest accounts as proportion of total arrests
    locationtotals.columns=["Count"]
    locationtotals.sort_values(by="Count", inplace=True, ascending=False)
    locationtotals["Count"] = locationtotals["Count"]/arrestscount

    # get cumulative sum
    locationtotals["Cumul"] = locationtotals["Count"].cumsum()
    locationtotals.reset_index(inplace=True)

    # identify the street segments that contribute to the concentration threshold
    hotspots = locationtotals.loc[locationtotals["Cumul"] <= threshold]

    # print the contributing fractions
    if output == True:
        contributingfrac = len(hotspots)/len(locationtotals)
        print("{}% of street segments account for {}% of arrests".format(round(100*contributingfrac, 2), 100*threshold))

    # save the list of hotspots to a file
    with resources.path(assets, "hotspots_micro.json") as outfile:
        hotspots.to_json(outfile)

    # return the list of hotspots
    return hotspots


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME: HoutSpots_micro
#DESCRIPTION: Determine the micro-geographic concentration of arrests

def HotSpots_meso(arrests_df, topN=5):

    # identify the 5 census tracts in each borough with highest concentrations of arrests
    for boro in ["M", "K", "B", "Q", "S"]:
        mydf = arrests_df.groupby(["arrest_boro", "OBJECTID"]).agg(count=("arrest_key", "count"))
        mydf.sort_values(["arrest_boro", "count"], ascending=False, inplace=True)
        badtracts = mydf.loc[boro].head(topN)

        if 'hotspots' in locals():
            hotspots = pd.concat([hotspots, badtracts])
        else:
            hotspots = badtracts

    hotspots.reset_index(inplace=True)

    # read in census tract GIS data
    with resources.path("DATA9003.assets", "censustracts.geojson") as censusfile:
        census = gpd.read_file(censusfile)
        census = census[["OBJECTID", "geometry"]]

    # match hotspots to GIS data & get centre
    hotspots=pd.merge(census,
                      hotspots,
                      how="right",
                      on="OBJECTID")

    hotspots["point"] = hotspots.geometry.representative_point()

    # get lat and long from GIS object
    hotspots["longitude"] = hotspots.point.x
    hotspots["latitude"] = hotspots.point.y

    # return ID and central coords of hotspot census tracts
    hotspots = hotspots[["OBJECTID", "latitude", "longitude"]]

    with resources.path("DATA9003.assets", "hotspots_meso.json") as outfile:
        hotspots.to_json(outfile)

    return hotspots
