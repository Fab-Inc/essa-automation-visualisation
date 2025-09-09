import ast
import pandas as pd
import numpy as np

def col_cleaning(df, col_name):
    print({col_name:df[col_name].unique()}, "\n")


def country_cleaning_(df, col, country_dict):
    for k,row in df.iterrows():
        update_countries = []
        countries = row[col]
        for country in countries:
            if country in country_dict:
                country = country_dict[country]
        
        update_countries.append(country)

        df.at[k,col] = update_countries

def country_cleaning(df, col, country_dict):
    """
    Normalize country/alias values in df[col] using mapping dict.
    df[col] is expected to contain lists of country strings.
    """
    def normalize_list(countries):
        update_countries = []
        if pd.isna(countries):
            return
        for country in countries.split(","):
            if not isinstance(country, str):
                continue
            # normalize key for lookup
            key = country.strip()
            mapped = country_dict.get(key, country)  # fallback to original if not found
            update_countries.append(mapped)
        return ", ".join(update_countries)

    df[col] = df[col].apply(lambda x: normalize_list(x) if isinstance(x, str) else x)
    return df

### user processing. if user is student, product type should be learning, if teacher, then teaching, if school, admin works etc.
def verify_user_product_type():
    pass


#%%
def clean_agents_data(value):
    #value = row["variable_value"]
    if pd.isna(value) or isinstance(value, int):
        return value
    
    if (value.startswith("[") and value.endswith("]")) or (value.startswith("{") and value.endswith("}")):
        try:
            df = ast.literal_eval(value)
            rl_vals = []
            if isinstance(df, dict):
                rl_vals.append(df[list(df.keys())[0]])
            else:
                for f in df:
                    if isinstance(f, dict):
                        #fg.append(", ".join(list(f.keys())))
                        if "name" in f:
                            rl_vals.append(f["name"])
                        elif "value" in f:
                            rl_vals.append(f["value"])
                        elif "use_case" in f:
                            rl_vals.append(f["use_case"])
                        elif "type" in f:
                            rl_vals.append(f["type"])
                        elif "Other" in f:
                            rl_vals.append("Other")
                        else:
                            rl_vals.append(f[list(f.keys())[0]]) ## take first key
                    else:
                        rl_vals.append(f)
            try:
                return ", ".join(rl_vals)
            except:
                if isinstance(rl_vals[0], int):
                    return rl_vals[0]
                else:
                    return ", ".join(rl_vals[0])
                
        except:
            return value
    else:
        return value

##
def clean_users(value, user1, user2):
    if pd.isna(value):
        return value
    if isinstance(value, int):
        return value
    if "not stated" in value.lower():
        return np.nan
    if user1 in value.lower():
        return value.split(" ")[0].strip().replace(",","").replace("+","").strip()
    if user2 in value.lower():
        return value.split(" ")[0].strip().replace(",","").replace("+","").strip()
    if "+" in value:
        return value.replace("+","").replace(",","").strip()
    if "crore" in value.lower():
        rec = value.split()[0].strip().replace(",","")
        try:
            return int(float(rec)*10000000)
        except:
            return value
    else:
        return value.replace(",","").strip()


def capitalize_values(value):
    if pd.isna(value):
        return value
    if isinstance(value, int):
        return value
    
    return ",".join([v.strip().title() if pd.notna(v) else "" for v in value.split(",")])