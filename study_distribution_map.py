#%%
from pathlib import Path
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd

from src.get_countries import retrieve_countries, country_iso_standards
from src.process import ( 
    country_cleaning
)

from functions import (
    plot_country_distribution_by_tier, 
    plot_tier_distribution, 
    country_to_region,
    plot_region_distribution_by_tier,
    plot_studyyear_distribution_by_tier
)

home = Path.home()
if home.name == "evans":
    home = Path("D:/Dropbox")

#%%
# load yaml file with parameters
with open("config.yaml", 'r') as file:
    params = yaml.safe_load(file)

evidence_path = home / params["evidence_path"]
region_path = params["regions"]
wiki_countries_URL = params["wiki_countries_url"]
country_iso_url = params["country_codes_url"]
headers = params["headers"]

# %%
evidence_data = pd.read_csv(evidence_path)
evidence_data["study_year"] = evidence_data["study_date"].apply(lambda x: pd.to_datetime(x).year if len(x.split("-")) >= 2 else x)
region_data = pd.read_csv(region_path, encoding="cp1252")
region_data["country"] = region_data["country"].str.replace("'","").str.replace(",","").str.replace('"','').str.strip()
region_data.dropna(subset=["class_region"], inplace=True, ignore_index=True)
region_data_dict = region_data.set_index("country")["class_region"].to_dict()

# %%
# Add Tier to make it clear during visuals
evidence_data["validation_number"] = "Tier-"+evidence_data["validation_number"].astype(str)

# %%
# %%
### map ISO-2 countries to their official names
standard_countries = country_iso_standards(country_iso_url, headers)
# standard_countries.loc[
#     standard_countries["iso_name"] == "Namibia", "iso_2"
# ] = "NA"
alternative_countries = retrieve_countries(wiki_countries_URL, headers)
alternative_countries[0].loc[
    alternative_countries[0]["Official name"] == "Kosovo", "iso_3"
] = "XKX"
clean_countries = alternative_countries[0][alternative_countries[0]["iso_3"] != '']
merged_countries = clean_countries.merge(standard_countries[["iso_2", "iso_3"]], on="iso_3")
alt_country_dict = merged_countries.set_index("iso_3")["Official name"].to_dict()
alt_country_dict.update(merged_countries.set_index("iso_2")["Official name"].to_dict())
alternative_countries = retrieve_countries(wiki_countries_URL, headers)
[country_cleaning(evidence_data, "country_of_study", alt_country_dict) ]


# get regions for the countries
evidence_data["region"] = evidence_data["country_of_study"].apply(
    lambda x: country_to_region(x, region_data_dict)
)

# %%
# country distribution by tier
df = evidence_data.copy()

def plot_study_distribution_by_country_geopandas(
    df,
    country_col="country_of_study",
    figsize=(12, 6),
    cmap="inferno",
    save_path=None,
    shapefile_path="data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp",  # Update with your path
    label = "all"
):
    # Step 1: Expand multi-country cells
    df = df.assign(**{country_col: df[country_col].astype(str).str.split(",")})
    df = df.explode(country_col)
    df[country_col] = df[country_col].str.strip()

    # Step 2: Drop blanks/NaNs/"nan"
    df = df[
        df[country_col].notna()
        & (df[country_col] != "")
        & (df[country_col].str.lower() != "nan")
    ].copy()

    # Step 3: Standardize country names
    country_mapping = {
        "Côte d'Ivoire": "Ivory Coast",
        "Democratic Republic of Congo": "Democratic Republic of the Congo",
        "Eswatini": "eSwatini",
        "HK": "China",
        "NA":"Namibia",
        "PR":"Puerto Rico",
        "People's Republic of China": "China",
        "Republic of China (Taiwan)" : "Taiwan",
        "The Gambia": "Gambia",
        "XK": "Kosovo"
    }
    df[country_col] = df[country_col].replace(country_mapping)

    # study counts per country (unique products)
    agg_df = (
        df.groupby(country_col)["study_id"]
        .nunique()
        .reset_index(name="study_count")
    )

    # Compute percentages
    total_studies = agg_df["study_count"].sum()
    agg_df["percentage"] = (agg_df["study_count"] / total_studies * 100).round(1)

    # Load world map from local shapefile
    world = gpd.read_file(shapefile_path)
    
    # Merge study counts with world map
    world = world.merge(agg_df, how='left', left_on='SUBUNIT', right_on=country_col)
    # Fill NaN values (countries with no studies) with 0
    world['study_count'] = world['study_count'].fillna(0)
    world['percentage'] = world['percentage'].fillna(0)

    # Plot choropleth map
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    world.plot(
        column='study_count',
        ax=ax,
        cmap=cmap,
        legend=True,
        legend_kwds={
            'label': "Number of Studies",
            'orientation': "horizontal",
            'shrink': 0.6,
            'pad': 0.05
        },
        missing_kwds={
            'color': 'lightgrey',
            'label': 'No Data'
        }
    )
    ax.set_title(f"Geographical Distribution of {label} Studies (Total n={total_studies})", pad=20)
    ax.axis('off')

    # Step 8: Save and show
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()

    return fig, world


# %%
## all studies
plot_study_distribution_by_country_geopandas(
    df,
    shapefile_path="data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp",
    save_path="data/charts/study_distribution_all.png"
)

## ESSA eligible
essa_df = evidence_data[evidence_data["validation_number"] != "Tier-5"]
plot_study_distribution_by_country_geopandas(
    essa_df,
    shapefile_path="data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp",
    save_path="data/charts/study_distribution_essa_eligible.png",
    label="ESSA-Eligible"
)

## ESSA level 1
essa_df = evidence_data[evidence_data["validation_number"] == "Tier-1"]
plot_study_distribution_by_country_geopandas(
    essa_df,
    shapefile_path="data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp",
    save_path="data/charts/study_distribution_essa_lvl_1.png",
    label="ESSA level 1"
)

## ESSA level 2
essa_df = evidence_data[evidence_data["validation_number"] == "Tier-2"]
plot_study_distribution_by_country_geopandas(
    essa_df,
    shapefile_path="data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp",
    save_path="data/charts/study_distribution_essa_lvl_2.png",
    label="ESSA level 2"
)

## ESSA level 3
essa_df = evidence_data[evidence_data["validation_number"] == "Tier-3"]
plot_study_distribution_by_country_geopandas(
    essa_df,
    shapefile_path="data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp",
    save_path="data/charts/study_distribution_essa_lvl_3.png",
    label="ESSA level 3"
)

## ESSA level 4
essa_df = evidence_data[evidence_data["validation_number"] == "Tier-4"]
plot_study_distribution_by_country_geopandas(
    essa_df,
    shapefile_path="data/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp",
    save_path="data/charts/study_distribution_essa_lvl_4.png",
    label="ESSA level 4"
)

# %%
