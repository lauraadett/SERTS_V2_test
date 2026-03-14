# -*- coding: utf-8 -*-
# SERTS LCOH Dashboard – Streamlit app for Heat Pump vs Gas Boiler

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Korrekturfaktor für COP aus EN14511-Stützpunkten
CORRECTION_FACTOR = 0.85

# Set global matplotlib font sizes for consistent visuals
plt.rcParams.update({
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'legend.fontsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
})

# -----------------------------
# Constants & Configuration
# -----------------------------
VAT_RATE = 0.19

# -----------------------------
# Streamlit Page Configuration
# -----------------------------
st.set_page_config(page_title="LCOH Dashboard", layout="wide")
st.title("🔥 Heat Pump vs Gas Boiler - LCOH Analysis")

# -----------------------------
# COP Support Data & Scenario Constants
# Updated: Datenblatt-Mittelwerte aus 20 Herstellerdatasheets (EN14511, A/W35)
# Hersteller: Stiebel Eltron, Vaillant, Wolf, Viessmann, Bosch
# Klassen: small <8kW, medium 8-11kW, large >11kW
# CORRECTION_FACTOR 0.85 wird separat in cop_interpolated() angewendet
# -----------------------------
COP_SUPPORT_W35 = {
    "small":  {-7: 2.97, 2: 4.26, 7: 5.26},
    "medium": {-7: 2.97, 2: 4.40, 7: 5.45},
    "large":  {-7: 2.68, 2: 4.06, 7: 5.29},
}
TEMP_WEIGHTS = {-7: 0.25, 2: 0.45, 7: 0.30}
SIZE_CLASSES = ["small", "medium", "large"]
SUPPLY_TEMPS = [35, 45, 55]

# -----------------------------
# Sidebar: Input Parameters
# -----------------------------
st.sidebar.header("⚙️ Parameter Settings")

# --- System Lifetimes ---
st.sidebar.subheader("System Lifetimes")
lifetime_hp = st.sidebar.slider(
    "Heat Pump Lifetime [Years]",
    min_value=10, max_value=30, value=20, step=1, key="lifetime_hp_slider"
)
lifetime_gb = st.sidebar.slider(
    "Gas Boiler Lifetime [Years]",
    min_value=10, max_value=30, value=15, step=1, key="lifetime_gb_slider"
)
discount_rate = st.sidebar.slider(
    "Discount Rate [-]",
    min_value=0.0, max_value=0.10, value=0.05, step=0.01, key="discount_rate_slider"
)

# --- Heat Demand ---
A = st.sidebar.slider(
    "Heated floor area A [m²]",
    min_value=50, max_value=300, value=130, step=10, key="area_slider"
)
q = st.sidebar.slider(
    "Specific heat demand q [kWh/(m²·a)]",
    min_value=30, max_value=150, value=120, step=5, key="q_slider"
)
Q_heat = A * q

# --- Heat Pump Parameters ---
st.sidebar.subheader("Heat Pump Parameters")
size_class = st.sidebar.selectbox("Size Class", options=SIZE_CLASSES, index=1, key="size_class_hp")
ef_grid = st.sidebar.slider(
    "Grid Emission Factor [kg CO2/kWh]",
    min_value=0.147, max_value=0.552, value=0.326, step=0.001,
    help="0.147 (Summer), 0.326 (Annual Avg), 0.552 (Winter Peak)"
)
co2_price_tonne = st.sidebar.slider(
    "CO2 Price [€/tonne]",
    min_value=0, max_value=200, value=55, step=5,
    help="Set to 0 to calculate LCOH without carbon tax."
)
price_hp = st.sidebar.slider(
    "Electricity Price HP [€/kWh]",
    min_value=0.15, max_value=0.50, value=0.38, step=0.01
)
OPEX_hp = st.sidebar.slider(
    "OPEX Heat Pump [€/year]",
    min_value=50, max_value=500, value=200, step=25
)

st.sidebar.subheader("Heat Pump CAPEX Components")
hardware_defaults = {
    "small":  (10000, 16000, 10000),
    "medium": (14000, 20000, 17000),
    "large":  (18000, 26000, 21500),
}
hw_min, hw_max, hw_def = hardware_defaults.get(size_class, (10000, 16000, 13500))
hardware = st.sidebar.slider(
    "Hardware (Unit & Accessories) [€]",
    min_value=hw_min, max_value=hw_max, value=hw_def, step=100,
)
installation = st.sidebar.slider(
    "Installation (Mechanical/Hydraulic) [€]",
    min_value=4000, max_value=10000, value=6500, step=100,
)
electrical = st.sidebar.slider(
    "Electrical Installation [€]",
    min_value=1500, max_value=5000, value=2500, step=100,
)
other = st.sidebar.slider(
    "Other (Foundation/Hydraulic Balancing) [€]",
    min_value=1000, max_value=3000, value=1500, step=100,
)
subsidy_rate = st.sidebar.slider(
    "Subsidy Rate (Förderquote)",
    min_value=0.0, max_value=0.7, value=0.3, step=0.01,
)
vat_rate = st.sidebar.slider(
    "VAT Rate",
    min_value=0.0, max_value=1.0, value=0.19, step=0.01,
    help="Adjust the VAT rate (0% to 100%)"
)

# --- Gas Boiler Parameters ---
st.sidebar.subheader("Gas Boiler Parameters")
price_gas = st.sidebar.slider(
    "Gas Price [€/kWh]",
    min_value=0.05, max_value=0.20, value=0.120, step=0.005
)
OPEX_gb = st.sidebar.slider(
    "OPEX Gas Boiler [€/year]",
    min_value=100, max_value=500, value=350, step=25
)
COP_gb = st.sidebar.slider(
    "Gas Boiler Efficiency η [-]",
    min_value=0.70, max_value=0.99, value=0.88, step=0.01,
    help="Stock average ~0.88 (mix: ~55% condensing η≈0.93, ~25% low-temp η≈0.87, ~20% standard η≈0.76)"
)

st.sidebar.subheader("Gas Boiler CAPEX Components")
gb_hardware = st.sidebar.slider(
    "Hardware (Boiler & Accessories) [€]",
    min_value=5000, max_value=15000, value=8500, step=100,
)
gb_installation = st.sidebar.slider(
    "Installation (Mechanical/Hydraulic) [€]",
    min_value=2000, max_value=8000, value=4000, step=100,
)
gb_exhaust = st.sidebar.slider(
    "Exhaust System [€]",
    min_value=1000, max_value=4000, value=1500, step=100,
)
gb_other = st.sidebar.slider(
    "Other (Foundation/Permits) [€]",
    min_value=500, max_value=3000, value=1000, step=100,
)

# -----------------------------
# Emission Factors
# -----------------------------
ef_gas = 0.2356  # Fixed: Fossil Gas (UBA Germany baseline)

# -----------------------------
# COP & Energy Calculation Functions
# -----------------------------
def cop_interpolated(T_out, support_points: dict) -> float:
    """Interpolate COP for a given outdoor temperature and apply correction factor."""
    temps = np.array(sorted(support_points.keys()), dtype=float)
    cops  = np.array([support_points[t] for t in temps], dtype=float)
    return float(np.interp(T_out, temps, cops)) * CORRECTION_FACTOR

def annual_electricity_from_bins(Q_heat_kwh, support_points: dict, weights: dict) -> float:
    """Calculate annual electricity use from temperature bins and COPs."""
    e_el = 0.0
    for T, w in weights.items():
        cop_T = cop_interpolated(T, support_points)
        e_el += (Q_heat_kwh * w) / cop_T
    return e_el

def cop_carnot(T_hot_C, T_cold_C) -> float:
    """Carnot COP for given temperatures (Celsius)."""
    T_hot  = T_hot_C  + 273.15
    T_cold = T_cold_C + 273.15
    return T_hot / (T_hot - T_cold)

def derive_support_points_for_supply_temp(support_W35: dict, T_supply_C: float) -> dict:
    """Derive COP support points for a different supply temperature via Carnot scaling."""
    if T_supply_C == 35:
        return dict(support_W35)
    derived = {}
    for T_out, cop35 in support_W35.items():
        eta = cop35 / cop_carnot(35, T_out)
        derived[T_out] = eta * cop_carnot(T_supply_C, T_out)
    return derived

def effective_annual_cop(support_W35: dict, T_supply: int, weights: dict) -> float:
    """
    Calculate the effective annual COP (load-weighted harmonic mean over temperature bins).
    Formula: COP_eff = 1 / Σ(w_k / COP_k)
    Correction factor 0.85 is applied inside cop_interpolated().
    """
    support = derive_support_points_for_supply_temp(support_W35, T_supply)
    denom = sum(w / cop_interpolated(T, support) for T, w in weights.items())
    return 1.0 / denom

# -----------------------------
# CAPEX Calculations
# -----------------------------
hardware_display = hardware
net_sum    = hardware_display + installation + electrical + other
gross_sum  = net_sum * (1 + vat_rate)
eligible_costs = min(gross_sum, 30_000)
subsidy_amount = min(eligible_costs * subsidy_rate, 21_000)
capex_hp_computed = gross_sum - subsidy_amount

gb_net_sum  = gb_hardware + gb_installation + gb_exhaust + gb_other
gb_gross_sum = gb_net_sum * (1 + vat_rate)

# -----------------------------
# Parameter Dictionary
# -----------------------------
parameters = {
    "Q_heat":        Q_heat,
    "lifetime_hp":   lifetime_hp,
    "lifetime_gb":   lifetime_gb,
    "discount_rate": discount_rate,
    "price_hp":      price_hp,
    "CAPEX_hp":      capex_hp_computed,
    "OPEX_hp":       OPEX_hp,
    "price_gas":     price_gas,
    "CAPEX_gb":      gb_gross_sum,
    "OPEX_gb":       OPEX_gb,
    "COP_gb":        COP_gb,
    "co2_price_tonne": co2_price_tonne,
    "ef_grid":       ef_grid,
    "ef_gas":        ef_gas,
}

# -----------------------------
# Sidebar Summary
# -----------------------------
st.sidebar.subheader("📌 Current Parameters Summary")
st.sidebar.write(f"**Heat Demand:** {Q_heat:,.0f} kWh/year")
st.sidebar.write(f"**Heat Pump Lifetime:** {lifetime_hp} Years")
st.sidebar.write(f"**Gas Boiler Lifetime:** {lifetime_gb} Years")
st.sidebar.write(f"**Electricity Price HP:** {price_hp:.3f} €/kWh")
st.sidebar.write(f"**Gas Price:** {price_gas:.3f} €/kWh")

# -----------------------------
# KEY PARAMETERS BOX (new — transparency for Q_heat, COP, E_el)
# -----------------------------
st.subheader("📋 Key Model Parameters")

cop_eff = effective_annual_cop(COP_SUPPORT_W35[size_class], 35, TEMP_WEIGHTS)
E_el_annual = Q_heat / cop_eff
ann_gas_kwh = Q_heat / COP_gb

col_k1, col_k2, col_k3, col_k4 = st.columns(4)
col_k1.metric(
    label="Heat Demand Q",
    value=f"{Q_heat:,.0f} kWh/a",
    help=f"{A} m² × {q} kWh/(m²·a) = {Q_heat:,.0f} kWh/a"
)
col_k2.metric(
    label=f"Effective COP (W35, {size_class})",
    value=f"{cop_eff:.2f}",
    help=(
        f"Load-weighted harmonic mean over temperature bins:\n"
        f"-7°C (w=0.25), +2°C (w=0.45), +7°C (w=0.30)\n"
        f"Raw datasheet average × correction factor {CORRECTION_FACTOR}"
    )
)
col_k3.metric(
    label="Annual Electricity (HP, W35)",
    value=f"{E_el_annual:,.0f} kWh/a",
    help=f"Q_heat / COP_eff = {Q_heat:,.0f} / {cop_eff:.2f}"
)
col_k4.metric(
    label="Annual Gas Use (GB)",
    value=f"{ann_gas_kwh:,.0f} kWh/a",
    help=f"Q_heat / η_GB = {Q_heat:,.0f} / {COP_gb:.2f}"
)
st.caption(
    f"COP is based on EN 14511 datasheet averages (20 devices, 3 capacity classes) "
    f"× correction factor {CORRECTION_FACTOR} (field correction for part-load, defrost, auxiliaries). "
    f"W45/W55 derived via Carnot scaling. Gas boiler efficiency η = {COP_gb:.2f} (stock average)."
)
st.markdown("---")

# -----------------------------
# LCOH Calculation
# -----------------------------
def calculate_lcoh_scenarios(params):
    results = {}
    r      = params["discount_rate"]
    n_hp   = params["lifetime_hp"]
    n_gb   = params["lifetime_gb"]
    q_heat = params["Q_heat"]
    co2_price = params["co2_price_tonne"]

    npv_heat = sum(q_heat / ((1 + r) ** t) for t in range(1, n_hp + 1))

    # Gas Boiler
    annual_gas_kwh        = q_heat / params["COP_gb"]
    annual_fuel_cost_gb   = annual_gas_kwh * params["price_gas"]
    annual_co2_tonnes_gb  = (annual_gas_kwh * params["ef_gas"]) / 1000
    annual_co2_tax_gb     = annual_co2_tonnes_gb * co2_price
    total_annual_cost_gb  = annual_fuel_cost_gb + params["OPEX_gb"] + annual_co2_tax_gb
    npv_cost_gb = params["CAPEX_gb"] + sum(
        total_annual_cost_gb / ((1 + r) ** t) for t in range(1, n_gb + 1)
    )
    lcoh_gb = npv_cost_gb / npv_heat

    # Heat Pump (all scenarios)
    for sc in SIZE_CLASSES:
        support_W35 = COP_SUPPORT_W35[sc]
        for T_supply in SUPPLY_TEMPS:
            support = derive_support_points_for_supply_temp(support_W35, T_supply)
            annual_elec_kwh      = annual_electricity_from_bins(q_heat, support, TEMP_WEIGHTS)
            annual_fuel_cost_hp  = annual_elec_kwh * params["price_hp"]
            annual_co2_tonnes_hp = (annual_elec_kwh * params["ef_grid"]) / 1000
            annual_co2_tax_hp    = annual_co2_tonnes_hp * co2_price
            total_annual_cost_hp = annual_fuel_cost_hp + params["OPEX_hp"] + annual_co2_tax_hp
            npv_cost_hp = params["CAPEX_hp"] + sum(
                total_annual_cost_hp / ((1 + r) ** t) for t in range(1, n_hp + 1)
            )
            lcoh_hp = npv_cost_hp / npv_heat
            results[(sc, T_supply)] = {
                "Heat Pump":       lcoh_hp,
                "Gas Boiler":      lcoh_gb,
                "annual_elec_kwh": annual_elec_kwh,
                "annual_gas_kwh":  annual_gas_kwh,
            }
    return results

scenario_results = calculate_lcoh_scenarios(parameters)

# -----------------------------
# Cumulative Cost Function
# -----------------------------
def calculate_cumulative_costs(params, sc, T_supply):
    r      = params["discount_rate"]
    n      = params["lifetime_hp"]
    support_W35 = COP_SUPPORT_W35[sc]
    support = derive_support_points_for_supply_temp(support_W35, T_supply)
    annual_elec_kwh     = annual_electricity_from_bins(params["Q_heat"], support, TEMP_WEIGHTS)
    annual_fuel_cost_hp = annual_elec_kwh * params["price_hp"]
    annual_co2_hp       = (annual_elec_kwh * params["ef_grid"]) / 1000 * params["co2_price_tonne"]
    annual_total_hp     = annual_fuel_cost_hp + params["OPEX_hp"] + annual_co2_hp

    annual_gas_kwh      = params["Q_heat"] / params["COP_gb"]
    annual_fuel_cost_gb = annual_gas_kwh * params["price_gas"]
    annual_co2_gb       = (annual_gas_kwh * params["ef_gas"]) / 1000 * params["co2_price_tonne"]
    annual_total_gb     = annual_fuel_cost_gb + params["OPEX_gb"] + annual_co2_gb

    years  = list(range(0, n + 1))
    cum_hp = [params["CAPEX_hp"]]
    cum_gb = [params["CAPEX_gb"]]
    for t in range(1, n + 1):
        df = 1 / ((1 + r) ** t)
        cum_hp.append(cum_hp[-1] + annual_total_hp * df)
        cum_gb.append(cum_gb[-1] + annual_total_gb * df)
    return years, cum_hp, cum_gb

# -----------------------------
# Row 1: LCOH Comparison & Investment Breakdown
# -----------------------------
col_lcoh, col_invest = st.columns(2)

with col_lcoh:
    st.subheader("📊 LCOH Comparison")
    st.markdown(
        f"<span style='font-size:1.35em; font-weight:600;'>Heat Pump "
        f"(<span style='color:#D62728; font-weight:800;'>{size_class.capitalize()}</span>) "
        f"vs Gas Boiler</span>",
        unsafe_allow_html=True
    )
    labels  = [f"W{T}" for T in SUPPLY_TEMPS]
    hp_vals = [scenario_results[(size_class, T)]["Heat Pump"] for T in SUPPLY_TEMPS]
    gb_val  = scenario_results[(size_class, SUPPLY_TEMPS[0])]["Gas Boiler"]

    fig1, ax1 = plt.subplots(figsize=(10, 7))
    x     = np.arange(len(labels))
    width = 0.38
    bars_hp = ax1.bar(x, hp_vals, width, label="Heat Pump", color="coral")
    ax1.bar(len(labels), gb_val, width, label="Gas Boiler", color="steelblue")
    ax1.text(len(labels), gb_val + 0.001, f"{gb_val:.4f}",
             ha="center", va="bottom", fontsize=9, fontweight="bold")
    for i, b in enumerate(bars_hp):
        y = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2, y + 0.001, f"{y:.4f}",
                 ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax1.set_xticks(list(x) + [len(labels)])
    ax1.set_xticklabels(labels + ["Gas Boiler"], fontsize=11, fontweight="bold")
    ax1.set_ylabel("Levelized Cost of Heat (€/kWh)", fontsize=13, fontweight="bold")
    ax1.grid(axis="y", linestyle="--", alpha=0.7)
    ax1.legend(fontsize=13, loc="upper left", frameon=False)
    ax1.tick_params(axis='y', labelsize=11)
    st.pyplot(fig1)

with col_invest:
    st.subheader("🧾 Breakdown of Investment Costs")
    st.markdown("<span style='opacity:0;'>.</span>", unsafe_allow_html=True)
    col_stack, col_rest = st.columns([0.99, 0.01])
    with col_stack:
        fig_stack, ax_stack = plt.subplots(figsize=(10, 7))
        segment_labels = ["Hardware", "Installation", "Electrical/Exhaust", "Other", "VAT"]
        segment_colors = ["#2E5077", "#4DA1A9", "#79D7BE", "#F6F4EB", "#C9C9C9"]
        hp_segments = [hardware_display, installation, electrical, other, net_sum * vat_rate]
        hp_bottom = 0
        for val, lab, col in zip(hp_segments, segment_labels, segment_colors):
            ax_stack.bar(0, val, bottom=hp_bottom, color=col, width=0.5)
            if val > 200:
                pct = (val / net_sum) * 100
                tcol = '#cccccc' if lab == "Other" else 'white'
                ax_stack.text(0, hp_bottom + val/2, f"{pct:.0f}%",
                              ha='center', va='center', color=tcol, fontweight='bold', fontsize=11)
            hp_bottom += val
        gb_segments = [gb_hardware, gb_installation, gb_exhaust, gb_other, gb_net_sum * vat_rate]
        gb_bottom = 0
        for val, lab, col in zip(gb_segments, segment_labels, segment_colors):
            ax_stack.bar(1, val, bottom=gb_bottom, color=col, width=0.5)
            if val > 200:
                pct = (val / gb_net_sum) * 100
                tcol = '#888888' if lab == "Other" else 'white'
                ax_stack.text(1, gb_bottom + val/2, f"{pct:.0f}%",
                              ha='center', va='center', color=tcol, fontweight='bold', fontsize=11)
            gb_bottom += val
        y_offset = 200
        subsidy = subsidy_amount
        ax_stack.plot([-0.3, 0.3], [hp_bottom, hp_bottom],
                      color='#333333', linestyle='--', linewidth=0.8, zorder=4)
        ax_stack.text(-0.65, hp_bottom + y_offset, 'Before Subsidies',
                      va='bottom', ha='center', fontweight='bold', fontsize=13, color='#333333')
        ax_stack.text(0.3, hp_bottom + y_offset, f'€{hp_bottom:,.0f}',
                      va='bottom', ha='left', fontweight='bold', fontsize=13, color='#333333')
        if subsidy > 0:
            ax_stack.plot([-0.3, 0.3], [capex_hp_computed, capex_hp_computed],
                          color='#D62728', linestyle='-', linewidth=1.0, zorder=5)
            ax_stack.text(-0.65, capex_hp_computed + y_offset, 'After Subsidies',
                          va='bottom', ha='center', fontweight='bold', fontsize=13, color='#D62728')
            ax_stack.text(0.3, capex_hp_computed + y_offset, f'€{capex_hp_computed:,.0f}',
                          va='bottom', ha='left', fontweight='bold', fontsize=13, color='#D62728')
        ax_stack.plot([0.7, 1.3], [gb_bottom, gb_bottom],
                      color='#333333', linestyle='--', linewidth=0.8, zorder=4)
        ax_stack.text(1.85, gb_bottom + y_offset, 'Total',
                      va='bottom', ha='center', fontweight='bold', fontsize=13, color='#333333')
        ax_stack.text(1.3, gb_bottom + y_offset, f'€{gb_bottom:,.0f}',
                      va='bottom', ha='left', fontweight='bold', fontsize=13, color='#333333')
        ax_stack.set_xlim(-1.1, 2.1)
        ax_stack.set_xticks([0, 1])
        ax_stack.set_xticklabels(['Heat Pump', 'Gas Boiler'], fontsize=15, fontweight='bold')
        ax_stack.set_ylabel('Price in €', fontsize=15, fontweight='bold')
        ax_stack.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}k'))
        legend_handles = [plt.Rectangle((0,0),1,1, facecolor=c, label=l)
                          for c, l in zip(segment_colors, segment_labels)]
        ax_stack.legend(handles=legend_handles, loc='upper left', fontsize=13, frameon=False)
        ax_stack.grid(axis='y', alpha=0.2, linestyle=':')
        ax_stack.set_ylim(0, 50000)
        plt.tight_layout()
        st.pyplot(fig_stack)

st.markdown("<br><br>", unsafe_allow_html=True)

# -----------------------------
# Row 2: Cumulative Cost & COP Curves (side by side, 50/50)
# -----------------------------
col_cum, col_cop = st.columns(2)

with col_cum:
    st.subheader("💰 Cumulative Discounted Cost Comparison")
    fig_cum, ax_cum = plt.subplots(figsize=(8, 6))
    colors_supply = {35: "coral", 45: "orange", 55: "red"}
    for T_supply in SUPPLY_TEMPS:
        years, cum_hp, cum_gb = calculate_cumulative_costs(parameters, size_class, T_supply)
        ax_cum.plot(years, [v / 1000 for v in cum_hp],
                    label=f"Heat Pump {size_class} W{T_supply}",
                    color=colors_supply[T_supply], linewidth=2)
    years, _, cum_gb = calculate_cumulative_costs(parameters, size_class, SUPPLY_TEMPS[0])
    ax_cum.plot(years, [v / 1000 for v in cum_gb],
                label="Gas Boiler", color="steelblue", linewidth=2.5, linestyle="--")
    # Break-even annotations
    for T_supply in SUPPLY_TEMPS:
        years_be, cum_hp_be, cum_gb_be = calculate_cumulative_costs(parameters, size_class, T_supply)
        for i in range(1, len(years_be)):
            if cum_hp_be[i-1] > cum_gb_be[i-1] and cum_hp_be[i] <= cum_gb_be[i]:
                frac = (cum_gb_be[i-1] - cum_hp_be[i-1]) / (
                    (cum_hp_be[i] - cum_hp_be[i-1]) - (cum_gb_be[i] - cum_gb_be[i-1])
                )
                be_year = (i - 1) + frac
                be_cost = (cum_hp_be[i-1] + frac * (cum_hp_be[i] - cum_hp_be[i-1])) / 1000
                ax_cum.axvline(x=be_year, color=colors_supply[T_supply],
                               linestyle=":", linewidth=1, alpha=0.7)
                ax_cum.annotate(
                    f"Break-even W{T_supply}\nyr {be_year:.1f}",
                    xy=(be_year, be_cost),
                    xytext=(be_year + 0.5, be_cost + 1),
                    fontsize=8, color=colors_supply[T_supply],
                    arrowprops=dict(arrowstyle="->", color=colors_supply[T_supply], lw=1)
                )
                break
    ax_cum.set_xlabel("Year", fontsize=12, fontweight="bold")
    ax_cum.set_ylabel("Cumulative Discounted Cost (k€)", fontsize=12, fontweight="bold")
    ax_cum.grid(True, linestyle="--", alpha=0.5)
    ax_cum.legend(fontsize=10, frameon=False)
    ax_cum.tick_params(labelsize=10)
    plt.tight_layout()
    st.pyplot(fig_cum)

with col_cop:
    st.subheader("📈 COP Curves – all sizes")
    temps_plot = np.linspace(-10, 12, 200)
    fig2, ax2 = plt.subplots(figsize=(8, 6))
    color_map = {
        ("small",  35): "yellow",  ("small",  45): "red",    ("small",  55): "green",
        ("medium", 35): "orange",  ("medium", 45): "pink",   ("medium", 55): "brown",
        ("large",  35): "lightblue",("large", 45): "purple", ("large",  55): "blue",
    }
    for sc in SIZE_CLASSES:
        support_base = COP_SUPPORT_W35[sc]
        for T_supply in SUPPLY_TEMPS:
            support = derive_support_points_for_supply_temp(support_base, T_supply)
            cops = [cop_interpolated(T, support) for T in temps_plot]
            ax2.plot(temps_plot, cops,
                     label=f"{sc} W{T_supply}",
                     color=color_map.get((sc, T_supply), "black"),
                     linewidth=2)
    ax2.set_xlabel("Outdoor temperature (°C)", fontsize=12, fontweight="bold")
    ax2.set_ylabel("COP", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.7)
    ax2.legend(fontsize=10, loc="upper left", frameon=False)
    ax2.tick_params(axis='x', labelsize=10)
    ax2.tick_params(axis='y', labelsize=10)
    plt.tight_layout()
    st.pyplot(fig2)

# -----------------------------
# Row 3: Environmental Analysis
# -----------------------------
st.subheader("🌍 Environmental Analysis")

support_ref = derive_support_points_for_supply_temp(COP_SUPPORT_W35["medium"], 45)
ann_gas_kwh_env = Q_heat / COP_gb
ann_el_kwh_env  = annual_electricity_from_bins(Q_heat, support_ref, TEMP_WEIGHTS)

ef_hp_scenarios = {
    "HP (Clean)":   0.147,
    "HP (Average)": 0.326,
    "HP (Dirty)":   0.552
}
emissions_gb_tonnes = (ann_gas_kwh_env * ef_gas) / 1000
hp_labels_env, hp_emissions_vals = [], []
for label, ef in ef_hp_scenarios.items():
    hp_labels_env.append(label)
    hp_emissions_vals.append((ann_el_kwh_env * ef) / 1000)

savings_vs_dirty = emissions_gb_tonnes - max(hp_emissions_vals)

col_env_chart, col_env_text = st.columns(2)

with col_env_chart:
    fig_env, ax_env = plt.subplots(figsize=(8, 5))
    bars_hp_env = ax_env.bar(hp_labels_env, hp_emissions_vals,
                              color='#2ecc71', alpha=0.8, label='Heat Pump Scenarios')
    ax_env.axhline(y=emissions_gb_tonnes, color='#e74c3c', linestyle='--', linewidth=3,
                   label=f'Gas Boiler Baseline ({emissions_gb_tonnes:.2f}t)')
    ax_env.set_ylabel("Annual CO2 Emissions (Tonnes)", fontsize=13, fontweight='bold')
    ax_env.set_title(f"Annual CO₂ Footprint — Q = {Q_heat:,} kWh/a",
                     fontsize=10, pad=15)
    ax_env.set_ylim(0, max(emissions_gb_tonnes, max(hp_emissions_vals)) * 1.3)
    ax_env.legend(fontsize=11, loc='upper left', frameon=False)
    ax_env.grid(axis='y', linestyle=':', alpha=0.6)
    ax_env.tick_params(axis='x', labelsize=10)
    ax_env.tick_params(axis='y', labelsize=10)
    for bar in bars_hp_env:
        yval = bar.get_height()
        ax_env.text(bar.get_x() + bar.get_width()/2, yval + 0.05, f"{yval:.2f}t",
                    ha='center', va='bottom', fontweight='bold', color='#27ae60', fontsize=9)
    plt.tight_layout()
    st.pyplot(fig_env)

with col_env_text:
    st.markdown(f"""
<div style='margin-bottom: 1.2em; padding: 1em; background: #ffeaea; border-radius: 8px;'>
    <b style='color:#e74c3c;'>Gas Boiler Baseline: ~{emissions_gb_tonnes:.2f} t CO₂/a</b><br>
    <span style='color:#e74c3c;'>
        Annual gas consumption: <b>{ann_gas_kwh_env:,.0f} kWh/a</b>
        (Q = {Q_heat:,} kWh/a ÷ η = {COP_gb:.2f})
    </span>
</div>
<div style='margin-bottom: 1.2em; padding: 1em; background: #eafaf1; border-radius: 8px;'>
    <b style='color:#27ae60;'>HP Max Saving (Summer): {emissions_gb_tonnes - min(hp_emissions_vals):.2f} t CO₂/a</b><br>
    <span style='color:#27ae60;'>
        Annual electricity consumption (HP, medium W45): <b>{ann_el_kwh_env:,.0f} kWh/a</b><br>
        Even in 'Dirty' winter conditions, the Heat Pump saves <b>{savings_vs_dirty:.2f} t CO₂/a</b>.
    </span>
</div>
""", unsafe_allow_html=True)
