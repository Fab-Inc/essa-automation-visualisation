#%%
from pathlib import Path
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
total_products = 287
products_with_studies = len(evidence_data["product_id"].unique())
proportion = round(products_with_studies / total_products, 2) * 100

# Add Tier to make it clear during visuals
evidence_data["validation_number"] = "Tier-"+evidence_data["validation_number"].astype(str)

# %%
validation_tiers = np.sort(evidence_data["validation_number"].unique())

# %%
plot_tier_distribution(evidence_data, total_products, save_path="data/charts/tier_distribution.png")

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
pivot_data = plot_country_distribution_by_tier(
    df,
    country_col="country_of_study",
    tier_col="validation_number",
    product_col="product_id",
    top_n=15,
    save_path="data/charts/country_distribution.png"
)

# %%
# region distribution by tier
plot_region_distribution_by_tier(
    evidence_data,
    save_path="data/charts/region_distribution.png"
)
# %%
# study year
plot_studyyear_distribution_by_tier(
    evidence_data,
    save_path="data/charts/studyyear_distribution.png"
)
# %%
