#%%
from pathlib import Path
import yaml
import pandas as pd
import json

from functions import (
    validator,
    plot_all_designs,
    plot_all_categories,
    plot_all_responses,
    create_ids_save
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

#%%
## validate some rejection cols which have similar values with their preceding columns
validator(evidence_data) # we can comment it out if we don't want this level of detail/consistency

# %%
## create labels to help with decongesting the x-axis labels
label_list = create_ids_save(evidence_data, "rejection_criterion_level")
label_dict = {}
label_dict_ = {}
for i in range(len(label_list)):
    label_dict_.update({f"R{i+1}":label_list[i]})
    label_dict.update({label_list[i]:f"R{i+1}"})

with open("data/labels_map_dict.json","w") as file:
    json.dump(label_dict, file, indent=4)

# %%
rj_cols = [
    'rejection_criterion_level_1',
    'rejection_criterion_level_2',
    'rejection_criterion_level_3',
    'rejection_criterion_level_4'
]
plot_all_responses(evidence_data, label_dict, label_dict_, rj_cols)

# %%
plot_all_categories(evidence_data, label_dict, rj_cols)

plot_all_designs(evidence_data, label_dict, rj_cols)