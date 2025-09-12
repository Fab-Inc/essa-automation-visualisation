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
        df.groupby([tier_col, country_col])[product_col]
        .nunique()
        .reset_index(name="product_count")
    )
    
    # Tier totals + percentages
    tier_country_counts["tier_total"] = (
        tier_country_counts.groupby(tier_col)["product_count"].transform("sum")
    )
    tier_country_counts["percentage"] = (
        tier_country_counts["product_count"] / tier_country_counts["tier_total"] * 100
    ).round(1)
    
    # Top N countries overall
    top_countries = (
        tier_country_counts.groupby(country_col)["product_count"]
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
    ax.set_ylabel("Percentage of products")
    ax.set_xlabel("Validation tier")
    ax.set_title(f"Distribution of Top {top_n} Countries within Each Validation Tier")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Country")
    plt.tight_layout()
    plt.xticks(rotation=0, ha="center")

    # ---- Add n=... labels here ----
    tier_totals = (
        df.groupby(tier_col)[product_col]
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
    ]

    tier_region_counts = (
        df.groupby([tier_col, region_col])[product_col]
        .nunique()
        .reset_index(name="product_count")
    )

    tier_region_counts["tier_total"] = (
        tier_region_counts.groupby(tier_col)["product_count"].transform("sum")
    )
    tier_region_counts["percentage"] = (
        tier_region_counts["product_count"] / tier_region_counts["tier_total"] * 100
    ).round(1)

    pivot_region = tier_region_counts.pivot(
        index=tier_col, columns=region_col, values="percentage"
    ).fillna(0)

    ax = pivot_region.plot(kind="bar", stacked=True, figsize=figsize, colormap=cmap)
    ax.set_ylabel("Percentage of products")
    ax.set_xlabel("Validation tier")
    ax.set_title("Distribution of Regions within Each Validation Tier")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Region")
    plt.tight_layout()
    plt.xticks(rotation=0, ha="center")

    # ---- Add n=... labels here ----
    tier_totals = (
        df.groupby(tier_col)[product_col]
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
        df.groupby([tier_col, year_col])[product_col]
        .nunique()
        .reset_index(name="product_count")
    )

    # Compute percentages
    tier_year_counts["tier_total"] = (
        tier_year_counts.groupby(tier_col)["product_count"].transform("sum")
    )
    tier_year_counts["percentage"] = (
        tier_year_counts["product_count"] / tier_year_counts["tier_total"] * 100
    ).round(1)

    # Pivot for stacked bar
    pivot_year = tier_year_counts.pivot(
        index=tier_col, columns=year_col, values="percentage"
    ).fillna(0)

    # Plot
    ax = pivot_year.plot(kind="bar", stacked=True, figsize=figsize, colormap=cmap)
    ax.set_ylabel("Percentage of products")
    ax.set_xlabel("Validation tier")
    ax.set_title("Distribution of Study Years within Each Validation Tier")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Study year")
    plt.tight_layout()
    plt.xticks(rotation=0, ha="center")

    # ---- Add n=... labels here ----
    tier_totals = (
        df.groupby(tier_col)[product_col]
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