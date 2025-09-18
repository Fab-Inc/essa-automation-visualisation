import pandas as pd
import matplotlib.pyplot as plt

def plot_tier_distribution(df, total_products, save_path=None):
    # Count unique products in each tier
    tier_counts = (
        df.groupby("validation_number")["product_id"]
        .nunique()
        .reset_index(name="count")
    )

    # Add percentage column
    tier_counts["percentage"] = (tier_counts["count"] / total_products * 100).round(1)
    #tier_counts["validation_number"] = "Tier-"+tier_counts["validation_number"].astype(str)

    
    plt.figure(figsize=(8,5))
    plt.bar(
        tier_counts["validation_number"].astype(str),
        tier_counts["percentage"],
        color="skyblue"
    )

    plt.xlabel("Validation tier")
    plt.ylabel("% of products")
    plt.title("Distribution of Products Across Validation Tiers")

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()

## mapping the countries to regions
def country_to_region(row, region_data_dict):
    """
    Map country (or list/comma-separated countries) to region(s) using region_data_dict.
    Returns comma-separated string of regions (with duplicates kept).
    """
    if pd.isna(row):
        return None
    
    if isinstance(row, str):
        countries = [c.strip() for c in row.split(",")]
    elif isinstance(row, list):
        countries = row
    else:
        countries = [row]

    regions = [region_data_dict[c] for c in countries if c in region_data_dict]
    return ",".join(regions) if regions else None

def plot_country_distribution_by_tier(
    df,
    country_col="country_of_study",
    tier_col="validation_number",
    product_col="product_id",
    top_n=15,
    figsize=(12,6),
    cmap="tab20",
    save_path = None
):
    # Drop actual NaN values first
    df = df.dropna(subset=[country_col]).copy()
    
    # Split and explode
    df[country_col] = df[country_col].astype(str).str.split(",")
    df = df.explode(country_col)
    df[country_col] = df[country_col].str.strip()
    
    # Drop leftover invalid entries ("", "nan", None)
    df = df[df[country_col].notna() & (df[country_col] != "") & (df[country_col].str.lower() != "nan")]
    
    # Count products per (tier, country)
    tier_country_counts = (
        df.groupby([tier_col, country_col])["study_id"]
        .nunique()
        .reset_index(name="count")
    )
    
    # Tier totals + percentages
    tier_country_counts["tier_total"] = (
        tier_country_counts.groupby(tier_col)["count"].transform("sum")
    )
    tier_country_counts["percentage"] = (
        tier_country_counts["count"] / tier_country_counts["tier_total"] * 100
    ).round(1)
    
    # Top N countries overall
    top_countries = (
        tier_country_counts.groupby(country_col)["count"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .index
    )
    tier_country_counts_top = tier_country_counts[
        tier_country_counts[country_col].isin(top_countries)
    ]
    
    # Pivot
    pivot_data = tier_country_counts_top.pivot(
        index=tier_col, columns=country_col, values="percentage"
    ).fillna(0)
    
    # Plot
    ax = pivot_data.plot(kind="bar", stacked=True, figsize=figsize, colormap=cmap)
    ax.set_ylabel("Percentage of studies")
    ax.set_xlabel("Validation tier")
    ax.set_title(f"Distribution of Studies Across the Top {top_n} Countries")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Country")
    plt.tight_layout()
    plt.xticks(rotation=0, ha="center")

    # ---- Add n=... labels here ----
    tier_totals = (
        df.groupby(tier_col)["study_id"]
        .nunique()
        .reindex(pivot_data.index)
        .reset_index(name="count")
    )

    # Loop over each tier (bar) by index
    for i, (tier, n) in enumerate(zip(tier_totals[tier_col], tier_totals["count"])):
        # Get the x-position for the i-th bar (each bar corresponds to a tier)
        x = i  # Bar positions are 0, 1, 2, ..., for each tier
        height = 100  # Stacked percentages always sum to 100
        ax.text(
            x, height + 2,  # Place slightly above the bar
            f"n={n}",
            ha="center", va="bottom", fontsize=10, fontweight="normal"
        )

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()
    
    return pivot_data

## plot region distribution by tiers
def plot_region_distribution_by_tier(
    df,
    region_col="region",
    tier_col="validation_number",
    product_col="product_id",
    figsize=(10,6),
    cmap="tab20",
    save_path=None  # <- optional: path to save file
):
    df = df.assign(**{region_col: df[region_col].astype(str).str.split(",")})
    df = df.explode(region_col)
    df[region_col] = df[region_col].str.strip()
    df = df[
        df[region_col].notna()
        & (df[region_col] != "")
        & (df[region_col].str.lower() != "nan")
        & (df["country_of_study"].notna())
    ]

    tier_region_counts = (
        df.groupby([tier_col, region_col])["study_id"]
        .nunique()
        .reset_index(name="count")
    )

    tier_region_counts["tier_total"] = (
        tier_region_counts.groupby(tier_col)["count"].transform("sum")
    )
    tier_region_counts["percentage"] = (
        tier_region_counts["count"] / tier_region_counts["tier_total"] * 100
    ).round(1)

    pivot_region = tier_region_counts.pivot(
        index=tier_col, columns=region_col, values="percentage"
    ).fillna(0)

    ax = pivot_region.plot(kind="bar", stacked=True, figsize=figsize, colormap=cmap)
    ax.set_ylabel("Percentage of studies")
    ax.set_xlabel("Validation tier")
    ax.set_title("Distribution of Studies Across the Regions")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Region")
    plt.tight_layout()
    plt.xticks(rotation=0, ha="center")

    # ---- Add n=... labels here ----
    tier_totals = (
        df.groupby(tier_col)["study_id"]
        .nunique()
        .reindex(pivot_region.index)
        .reset_index(name="count")
    )

    # Loop over each tier (bar) by index
    for i, (tier, n) in enumerate(zip(tier_totals[tier_col], tier_totals["count"])):
        # Get the x-position for the i-th bar (each bar corresponds to a tier)
        x = i  # Bar positions are 0, 1, 2, ..., for each tier
        height = 100  # Stacked percentages always sum to 100
        ax.text(
            x, height + 2,  # Place slightly above the bar
            f"n={n}",
            ha="center", va="bottom", fontsize=10, fontweight="normal"
        )

    # Save to file if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()

    return pivot_region

#%%
def plot_studyyear_distribution_by_tier(
    df,
    year_col="study_year",
    tier_col="validation_number",
    product_col="product_id",
    figsize=(12,6),
    cmap="tab20",
    save_path=None
):
    # Expand multi-year cells
    df = df.assign(**{year_col: df[year_col].astype(str).str.split(",")})
    df = df.explode(year_col)
    df[year_col] = df[year_col].str.strip()

    # Drop blanks/NaNs/"nan"
    df = df[
        df[year_col].notna()
        & (df[year_col] != "")
        & (df[year_col].str.lower() != "nan")
    ]

    # Convert to numeric
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df = df.dropna(subset=[year_col])
    df[year_col] = df[year_col].astype(int)

    # Count products per tier/year
    tier_year_counts = (
        df.groupby([tier_col, year_col])["study_id"]
        .nunique()
        .reset_index(name="count")
    )

    # Compute percentages
    tier_year_counts["tier_total"] = (
        tier_year_counts.groupby(tier_col)["count"].transform("sum")
    )
    tier_year_counts["percentage"] = (
        tier_year_counts["count"] / tier_year_counts["tier_total"] * 100
    ).round(1)

    # Pivot for stacked bar
    pivot_year = tier_year_counts.pivot(
        index=tier_col, columns=year_col, values="percentage"
    ).fillna(0)

    # Plot
    ax = pivot_year.plot(kind="bar", stacked=True, figsize=figsize, colormap=cmap)
    ax.set_ylabel("Percentage of studies")
    ax.set_xlabel("Validation tier")
    ax.set_title("Distribution of Studies Across the Years of Study")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Study year")
    plt.tight_layout()
    plt.xticks(rotation=0, ha="center")

    # ---- Add n=... labels here ----
    tier_totals = (
        df.groupby(tier_col)["study_id"]
        .nunique()
        .reindex(pivot_year.index)
        .reset_index(name="count")
    )

    # Loop over each tier (bar) by index
    for i, (tier, n) in enumerate(zip(tier_totals[tier_col], tier_totals["count"])):
        # Get the x-position for the i-th bar (each bar corresponds to a tier)
        x = i  # Bar positions are 0, 1, 2, ..., for each tier
        height = 100  # Stacked percentages always sum to 100
        ax.text(
            x, height + 2,  # Place slightly above the bar
            f"n={n}",
            ha="center", va="bottom", fontsize=10, fontweight="normal"
        )

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()

    return pivot_year

## this function will validate some of the columns left blank but share same criterion as the previous question
def validator(df):
    for i,row in df.iterrows():
        rej_keys = [key for key in row.keys() if "rejection_criterion" in key]
        validation_num = row["validation_number"]
        if validation_num == 1:
            if not all(pd.isna(row[rej_key]) for rej_key in rej_keys):
                print("Flag-0")
        elif validation_num == 2:
            if pd.isna(row[rej_keys[0]]):
                print("Flag-1-0")
            # if pd.isna(row[rej_keys[1]]):
            #     print("Flag-1-1")
            #     row[rej_keys[1]] = row[rej_keys[0]]
        elif validation_num == 3:
            if pd.isna(row[rej_keys[0]]):
                print("Flag-2-0")
            if pd.isna(row[rej_keys[1]]):
                print("Flag-2-1")
                df.loc[i, rej_keys[1]] = row[rej_keys[0]]
                
            # if pd.isna(row[rej_keys[2]]):
            #     print("Flag-2-2")
            #     row[rej_keys[2]] = row[rej_keys[1]]
        elif validation_num == 4:
            if pd.isna(row[rej_keys[0]]):
                print("Flag-3-0")
            if pd.isna(row[rej_keys[0]]):
                print("Flag-3-1")
                df.loc[i, rej_keys[1]] = row[rej_keys[0]]
            if pd.isna(row[rej_keys[2]]):
                print("Flag-3-2")
                df.loc[i, rej_keys[2]] = row[rej_keys[1]]
            # if pd.isna(row[rej_keys[3]]):
            #     print("Flag-3-3")
            #     row[rej_keys[3]] = row[rej_keys[2]]

## function to plot the rejection criterion levels across the design categories: 
def plot_rejection_criteria(df, label_dict, cols, d_label, ax):
    # Filter the df by the specified design number
    df_filtered = df[df["design_categorization_number"] == d_label].copy()

    # Iterate through the rejection criteria columns
    for i, col in enumerate(cols, start=1):
        new_labels = {}
        # Count the number of non-null responses for each rejection criterion level
        for _, row in df_filtered.iterrows():
            row_val = row[col]
            if pd.isna(row_val):
                continue
            else:
                response = label_dict.get(row_val, row_val)  # Default to row_val if label_dict doesn't have the key
                if response not in new_labels:
                    new_labels[response] = 0
                new_labels[response] += 1

        # Sort the labels by numeric value: R1,R2,R3.....
        labels_sort = {k: v for k, v in sorted(new_labels.items(), key=lambda item: int(item[0][1:]) if item[0][1:].isdigit() else item[0])}
        labels = list(labels_sort.keys())
        values = list(labels_sort.values())
        
        # Create a subplot for each rejection criterion level
        ax[i-1].bar(labels, values, color="skyblue")
        ax[i-1].set_xlabel("Response label")
        ax[i-1].set_ylabel("Total count")
        ax[i-1].set_title(f"Rejection Criterion Level {i}")
        ax[i-1].set_xticks(range(len(labels))) 
        ax[i-1].set_xticklabels(labels, rotation=45, ha="right")

def plot_all_designs(df, label_dict, cols):
    # Create a grid of subplots: 5 design categories, each with 4 subplots for the rejection criteria
    fig, axes = plt.subplots(5, 4, figsize=(20, 25)) 
    
    # Plot for each design categorization label (1 to 5)
    for d_label in range(1, 6):
        plot_rejection_criteria(df, label_dict, cols, d_label, axes[d_label - 1])
    
    # Adjust layout to prevent overlapping
    plt.tight_layout()
    plt.show()

## function to plot the total responses' count across the design categories:
def plot_by_category(df, label_dict, cols, d_label, ax):
    # Filter the dataframe for the given design categorization number
    df = df[df["design_categorization_number"] == d_label].copy()
    
    new_labels = {}
    for i, row in df.iterrows():
        for col in cols:
            row_val = row[col]
            if pd.isna(row_val):
                continue
            else:
                response = label_dict[row_val]
                if response not in new_labels:
                    new_labels[response] = 0
                new_labels[response] += 1
    
    # Sort the labels by numeric value in the label
    labels_sort = {k: v for k, v in sorted(new_labels.items(), key=lambda item: int(item[0][1:]))}
    labels = list(labels_sort.keys())
    values = list(labels_sort.values())

    # Plot on the given axis (ax)
    ax.bar(labels, values, color="skyblue")
    ax.set_xlabel("Response label")
    ax.set_ylabel("Total count")
    ax.set_title(f"Design Categorization {d_label}")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")  # Rotate the labels for better visibility

def plot_all_categories(df, label_dict, cols):
    
    fig, axes = plt.subplots(1, 5, figsize=(20, 5))
    
    # Plot for each design categorization label
    for d_label, ax in zip(range(1, 6), axes):
        plot_by_category(df, label_dict, cols, d_label, ax)
    
    # Adjust layout to prevent overlapping
    plt.tight_layout()
    plt.show()

# plot all the responses
def plot_all_responses(df, label_dict, label_dict_,cols):
    labels = list(label_dict.values())
    new_labels = {}
    for i,row in df.iterrows():
        for col in cols:
            row_val = row[col]
            if pd.isna(row_val):
                continue
            else:
                response = label_dict[row_val]
                if response not in new_labels:
                    new_labels[response] = 0
                new_labels[response] += 1
    
    labels_sort = {k:v for k,v in sorted(new_labels.items(), key=lambda item: int(item[0][1:]))}
    labels = list(labels_sort.keys())
    values = list(labels_sort.values())

    plt.figure(figsize=(8,5))
    plt.bar(
        labels,
        values,
        color="skyblue"
    )

    plt.xlabel("Response label")
    plt.ylabel("Total count")
    plt.title("Number of times the responses were mentioned")
    plt.show()
    
    return labels_sort

# function to create simple ids to label each response
def create_ids_save(df, col):
    all_labels = []
    for cl in range(1,5):
        col_name = f"{col}_{cl}"
        rejection = list(df[col_name].unique())
        rej_clean = [b for b in rejection if pd.notna(b)]
        [all_labels.append(v) for v in rej_clean if v not in all_labels]
    
    return all_labels