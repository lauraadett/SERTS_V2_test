
# -*- coding: utf-8 -*-
# SERTS LCOH Dashboard – Streamlit app for Heat Pump vs Gas Boiler

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

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
VAT_RATE = 0.19  # Default German VAT rate for residential heating systems

# -----------------------------
# Streamlit Page Configuration
# -----------------------------
st.set_page_config(page_title="LCOH Dashboard", layout="wide")
st.title("🔥 Heat Pump vs Gas Boiler - LCOH Analysis")

# -----------------------------
# COP Support Data & Scenario Constants
# -----------------------------
COP_SUPPORT_W35 = {
    "small":  {-7: 2.80,  2: 3.30,  7: 3.90},
    "medium": {-7: 2.70,  2: 3.20,  7: 3.80},
    "large":  {-7: 2.60,  2: 3.10,  7: 3.70},
}
TEMP_WEIGHTS = {-7: 0.25, 2: 0.45, 7: 0.30}
SIZE_CLASSES = ["small", "medium", "large"]
SUPPLY_TEMPS = [35, 45, 55]

# -----------------------------
# Sidebar: Input Parameters
# -----------------------------

st.sidebar.header("⚙️ Parameter Settings")

st.sidebar.subheader("Common Parameters")
Q_heat = st.sidebar.slider(
    "Heat Demand Q_heat [kWh/year]",
    min_value=5000, max_value=50000, value=20000, step=1000
)
lifetime = st.sidebar.slider(
    "Lifetime [Years]",
    min_value=10, max_value=50, value=20, step=1
)
discount_rate = st.sidebar.slider(
    "Discount Rate [-]",
    min_value=0.0, max_value=0.10, value=0.05, step=0.01
)

# --- Heat Pump Parameters ---
st.sidebar.subheader("Heat Pump Parameters")
size_class = st.sidebar.selectbox("Size Class", options=SIZE_CLASSES, index=1, key="size_class_hp")
ef_grid = st.sidebar.slider(
    "Grid Emission Factor [kg CO2/kWh]",
    min_value=0.147,
    max_value=0.552,
    value=0.326,
    step=0.001,
    help="0.147 (Summer), 0.326 (Annual Avg), 0.552 (Winter Peak)"
)
co2_price_tonne = st.sidebar.slider(
    "CO2 Price [€/tonne]",
    min_value=0, max_value=200, value=55, step=5,
    help="Set to 0 to calculate LCOH without carbon tax."
)
price_hp = st.sidebar.slider(
    "Electricity Price HP [€/kWh]",
    min_value=0.15,
    max_value=0.50,
    value=0.32,
    step=0.01
)
OPEX_hp = st.sidebar.slider(
    "OPEX Heat Pump [€/year]",
    min_value=50,
    max_value=500,
    value=200,
    step=25
)
st.sidebar.subheader("Heat Pump CAPEX Components")
hardware_defaults = {
    "small": (10000, 16000, 13500),
    "medium": (14000, 20000, 17000),
    "large": (18000, 26000, 21500),
}
hw_min, hw_max, hw_def = hardware_defaults.get(size_class, (10000, 16000, 13500))
hardware = st.sidebar.slider(
    "Hardware (Unit & Accessories) [€]",
    min_value=hw_min,
    max_value=hw_max,
    value=hw_def,
    step=100,
)
installation = st.sidebar.slider(
    "Installation (Mechanical/Hydraulic) [€]",
    min_value=4000,
    max_value=10000,
    value=6500,
    step=100,
)
electrical = st.sidebar.slider(
    "Electrical Installation [€]",
    min_value=1500,
    max_value=5000,
    value=2500,
    step=100,
)
other = st.sidebar.slider(
    "Other (Foundation/Hydraulic Balancing) [€]",
    min_value=1000,
    max_value=3000,
    value=1500,
    step=100,
)
subsidy_rate = st.sidebar.slider(
    "Subsidy Rate (Förderquote)",
    min_value=0.0,
    max_value=0.7,
    value=0.3,
    step=0.01,
)
vat_rate = st.sidebar.slider(
    "VAT Rate",
    min_value=0.0,
    max_value=1.0,
    value=0.19,
    step=0.01,
    help="Adjust the VAT rate (0% to 100%)"
)

# --- Gas Boiler Parameters ---
st.sidebar.subheader("Gas Boiler Parameters")
price_gas = st.sidebar.slider(
    "Gas Price [€/kWh]",
    min_value=0.05,
    max_value=0.20,
    value=0.120,
    step=0.005
)
OPEX_gb = st.sidebar.slider(
    "OPEX Gas Boiler [€/year]",
    min_value=100,
    max_value=500,
    value=350,
    step=25
)
COP_gb = st.sidebar.slider(
    "COP Gas Boiler [-]",
    min_value=0.80,
    max_value=0.99,
    value=0.95,
    step=0.01
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
# Emission Factors (needed for parameter dictionary)
# -----------------------------
ef_gas = 0.2356  # Fixed: Fossil Gas (UBA Germany baseline)

# -----------------------------
# Parameter Dictionary (for calculations)
# -----------------------------
parameters = {
    "Q_heat": Q_heat,
    "lifetime": lifetime,
    "discount_rate": discount_rate,
    "price_hp": price_hp,
    "OPEX_hp": OPEX_hp,
    "price_gas": price_gas,
    "OPEX_gb": OPEX_gb,
    "COP_gb": COP_gb,
    "co2_price_tonne": co2_price_tonne,
    "ef_grid": ef_grid,
    "ef_gas": ef_gas
}


# -----------------------------
# COP & Energy Calculation Functions
# -----------------------------
def cop_interpolated(T_out, support_points: dict) -> float:
    """Interpolate COP for a given outdoor temperature."""
    temps = np.array(sorted(support_points.keys()), dtype=float)
    cops  = np.array([support_points[t] for t in temps], dtype=float)
    return float(np.interp(T_out, temps, cops))

def annual_electricity_from_bins(Q_heat_kwh, support_points: dict, weights: dict) -> float:
    """Calculate annual electricity use from temperature bins and COPs."""
    e_el = 0.0
    for T, w in weights.items():
        cop_T = cop_interpolated(T, support_points)
        e_el += (Q_heat_kwh * w) / cop_T
    return e_el

def cop_carnot(T_hot_C, T_cold_C) -> float:
    """Carnot COP for given hot/cold temperatures (Celsius)."""
    T_hot = T_hot_C + 273.15
    T_cold = T_cold_C + 273.15
    return T_hot / (T_hot - T_cold)

def derive_support_points_for_supply_temp(support_W35: dict, T_supply_C: float) -> dict:
    """Derive COP support points for a different supply temperature."""
    if T_supply_C == 35:
        return dict(support_W35)
    derived = {}
    for T_out, cop35 in support_W35.items():
        eta = cop35 / cop_carnot(35, T_out)
        derived[T_out] = eta * cop_carnot(T_supply_C, T_out)
    return derived


# -----------------------------
# LCOH Calculation (with CO2 tax)
# -----------------------------
def calculate_lcoh_scenarios(params):
    """Calculate LCOH for all HP scenarios and a single Gas Boiler reference."""
    results = {}
    r = params["discount_rate"]
    n = params["lifetime"]
    q_heat = params["Q_heat"]
    co2_price = params["co2_price_tonne"]

    # Discounted sum of heat delivered
    npv_heat = sum(q_heat / ((1 + r) ** t) for t in range(1, n + 1))

    # --- Gas Boiler LCOH ---
    annual_gas_kwh = q_heat / params["COP_gb"]
    annual_fuel_cost_gb = annual_gas_kwh * params["price_gas"]
    annual_co2_tonnes_gb = (annual_gas_kwh * params["ef_gas"]) / 1000
    annual_co2_tax_gb = annual_co2_tonnes_gb * co2_price
    total_annual_cost_gb = annual_fuel_cost_gb + params["OPEX_gb"] + annual_co2_tax_gb
    npv_cost_gb = params["CAPEX_gb"] + sum(total_annual_cost_gb / ((1 + r) ** t) for t in range(1, n + 1))
    lcoh_gb = npv_cost_gb / npv_heat

    # --- Heat Pump LCOH (all scenarios) ---
    for size_class in SIZE_CLASSES:
        support_W35 = COP_SUPPORT_W35[size_class]
        for T_supply in SUPPLY_TEMPS:
            support = derive_support_points_for_supply_temp(support_W35, T_supply)
            annual_elec_kwh = annual_electricity_from_bins(q_heat, support, TEMP_WEIGHTS)
            annual_fuel_cost_hp = annual_elec_kwh * params["price_hp"]
            annual_co2_tonnes_hp = (annual_elec_kwh * params["ef_grid"]) / 1000
            annual_co2_tax_hp = annual_co2_tonnes_hp * co2_price
            total_annual_cost_hp = annual_fuel_cost_hp + params["OPEX_hp"] + annual_co2_tax_hp
            npv_cost_hp = params["CAPEX_hp"] + sum(total_annual_cost_hp / ((1 + r) ** t) for t in range(1, n + 1))
            lcoh_hp = npv_cost_hp / npv_heat
            results[(size_class, T_supply)] = {
                "Heat Pump": lcoh_hp,
                "Gas Boiler": lcoh_gb,
                "annual_elec_kwh": annual_elec_kwh,
                "annual_gas_kwh": annual_gas_kwh,
            }
    return results
# ============================================================
# Run Calculation (will be executed after CAPEX inputs below)
# ============================================================

# -----------------------------
# Detailed CAPEX component inputs
# -----------------------------

# No inclination surcharge anymore — use hardware value directly
hardware_display = hardware

# CAPEX formula with variable VAT rate

# --- CAPEX calculation and parameter update (single source of truth) ---
net_sum = hardware_display + installation + electrical + other
gross_sum = net_sum * (1 + vat_rate)  # Add variable VAT
capex_hp_computed = gross_sum * (1 - subsidy_rate)
gb_net_sum = gb_hardware + gb_installation + gb_exhaust + gb_other
gb_gross_sum = gb_net_sum * (1 + vat_rate)

# Always update parameters for all calculations (including LCOH, main, etc.)
parameters["CAPEX_hp"] = capex_hp_computed
parameters["CAPEX_gb"] = gb_gross_sum

# Display information about VAT in sidebar
st.sidebar.info(f"✓ All prices shown include {vat_rate*100:.0f}% VAT")




# Now run the scenarios with the computed CAPEX
scenario_results = calculate_lcoh_scenarios(parameters)




# --- First row: LCOH Comparison & Breakdown of Investment Costs ---
col_lcoh, col_invest = st.columns(2)
with col_lcoh:
    st.subheader("📊 LCOH Comparison")
    labels, hp_vals = [], []
    gb_val = None
    for size_class in SIZE_CLASSES:
        for T_supply in SUPPLY_TEMPS:
            row = scenario_results[(size_class, T_supply)]
            labels.append(f"{size_class}\nW{T_supply}")
            hp_vals.append(row["Heat Pump"])
            if gb_val is None:
                gb_val = row["Gas Boiler"]
    fig1, ax1 = plt.subplots(figsize=(10, 7))
    x = np.arange(len(labels))
    width = 0.38
    bars_hp = ax1.bar(x, hp_vals, width, label="Heat Pump", color="coral")
    # Draw a single Gas Boiler reference bar at the far right
    ax1.bar(len(labels), gb_val, width, label="Gas Boiler", color="steelblue")
    # Add label for the Gas Boiler bar
    ax1.text(len(labels), gb_val + 0.001, f"{gb_val:.4f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    # Add label for each Heat Pump bar
    for i, b in enumerate(bars_hp):
        y = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2, y + 0.001, f"{y:.4f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    # X-tick labels: all HP scenarios, then 'Gas Boiler'
    ax1.set_xticks(list(x) + [len(labels)])
    ax1.set_xticklabels(labels + ["Gas Boiler"], fontsize=11, fontweight="bold")
    ax1.set_ylabel("Levelized Cost of Heat (€/kWh)", fontsize=13, fontweight="bold")
    # Remove in-plot title for unified look
    # ax1.set_title("LCOH Comparison", fontsize=12, fontweight="bold")
    ax1.grid(axis="y", linestyle="--", alpha=0.7)
    ax1.legend(fontsize=13, loc="upper left", frameon=False)
    ax1.tick_params(axis='y', labelsize=11)
    st.pyplot(fig1)

with col_invest:
    st.subheader("🧾 Breakdown of Investment Costs")
    # ...existing investment breakdown code...
    col_stack, col_rest = st.columns([0.99, 0.01])
    with col_stack:
        fig_stack, ax_stack = plt.subplots(figsize=(10, 7))
        segment_labels = ["Hardware", "Installation", "Electrical/Exhaust", "Other", "VAT"]
        segment_colors = ["#2E5077", "#4DA1A9", "#79D7BE", "#F6F4EB", "#C9C9C9"]
        hp_segments = [hardware_display, installation, electrical, other, net_sum * vat_rate]
        hp_bottom = 0
        for val, lab, col in zip(hp_segments, segment_labels, segment_colors):
            ax_stack.bar(0, val, bottom=hp_bottom, color=col, width=0.5, label=None)
            if val > 200:
                percentage = (val / net_sum) * 100
                text_color = '#cccccc' if lab == "Other" else 'white'
                ax_stack.text(0, hp_bottom + val/2, f"{percentage:.0f}%", ha='center', va='center', color=text_color, fontweight='bold', fontsize=11)
            hp_bottom += val
        gb_segments = [gb_hardware, gb_installation, gb_exhaust, gb_other, gb_net_sum * vat_rate]
        gb_bottom = 0
        for val, lab, col in zip(gb_segments, segment_labels, segment_colors):
            ax_stack.bar(1, val, bottom=gb_bottom, color=col, width=0.5, label=None)
            if val > 200:
                percentage = (val / gb_net_sum) * 100
                text_color = '#888888' if lab == "Other" else 'white'
                ax_stack.text(1, gb_bottom + val/2, f"{percentage:.0f}%", ha='center', va='center', color=text_color, fontweight='bold', fontsize=11)
            gb_bottom += val
        y_offset = 200
        ax_stack.plot([-0.3, 0.3], [hp_bottom, hp_bottom], color='#333333', linestyle='--', linewidth=0.8, zorder=4)
        ax_stack.plot([-0.3, 0.3], [capex_hp_computed, capex_hp_computed], color='#D62728', linestyle='-', linewidth=1.0, zorder=5)
        ax_stack.text(-0.65, hp_bottom + y_offset, 'Before Subsidies', va='bottom', ha='center', fontweight='bold', fontsize=13, color='#333333')
        ax_stack.text(-0.65, capex_hp_computed + y_offset, 'After Subsidies', va='bottom', ha='center', fontweight='bold', fontsize=13, color='#D62728')
        ax_stack.text(0.3, hp_bottom + y_offset, f'€{hp_bottom:,.0f}', va='bottom', ha='left', fontweight='bold', fontsize=13, color='#333333')
        ax_stack.text(0.3, capex_hp_computed + y_offset, f'€{capex_hp_computed:,.0f}', va='bottom', ha='left', fontweight='bold', fontsize=13, color='#D62728')
        ax_stack.plot([0.7, 1.3], [gb_bottom, gb_bottom], color='#333333', linestyle='--', linewidth=0.8, zorder=4)
        ax_stack.text(1.85, gb_bottom + y_offset, 'Total', va='bottom', ha='center', fontweight='bold', fontsize=13, color='#333333')
        ax_stack.text(1.3, gb_bottom + y_offset, f'€{gb_bottom:,.0f}', va='bottom', ha='left', fontweight='bold', fontsize=13, color='#333333')
        ax_stack.set_xlim(-1.1, 2.1)
        ax_stack.set_xticks([0, 1])
        ax_stack.set_xticklabels(['Heat Pump', 'Gas Boiler'], fontsize=15, fontweight='bold')
        ax_stack.set_ylabel('Price in €', fontsize=15, fontweight='bold')
        ax_stack.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}k'))
        # Remove in-plot title for unified look
        # ax_stack.set_title('Breakdown of Investment Costs', fontsize=18, fontweight='bold', pad=18)
        legend_handles = [plt.Rectangle((0,0),1,1, facecolor=c, label=l) for c, l in zip(segment_colors, segment_labels)]
        ax_stack.legend(handles=legend_handles, loc='upper left', fontsize=13, frameon=False)
        ax_stack.grid(axis='y', alpha=0.2, linestyle=':')
        ax_stack.set_ylim(0, 50000)
        plt.tight_layout()
        st.pyplot(fig_stack)

    # Add vertical space between rows
    st.markdown("<br><br>", unsafe_allow_html=True)

# --- Second row: COP Curves & Gas Boiler Efficiency ---
col_cop, col_eff = st.columns(2)
with col_cop:
    st.subheader("📈 COP Curves – all sizes")
    temps_plot = np.linspace(-10, 12, 200)
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    color_map = {
        ("small", 35): "yellow",
        ("small", 45): "red",
        ("small", 55): "green",
        ("medium", 35): "orange",
        ("medium", 45): "pink",
        ("medium", 55): "brown",
        ("large", 35): "lightblue",
        ("large", 45): "purple",
        ("large", 55): "blue",
    }
    for size_class in SIZE_CLASSES:
        support_base = COP_SUPPORT_W35[size_class]
        for T_supply in SUPPLY_TEMPS:
            support = derive_support_points_for_supply_temp(support_base, T_supply)
            cops = [cop_interpolated(T, support) for T in temps_plot]
            color = color_map.get((size_class, T_supply), "black")
            ax2.plot(temps_plot, cops,
                     label=f"{size_class} W{T_supply}",
                     color=color,
                     linewidth=2)
    ax2.set_xlabel("Outdoor temperature (°C)", fontsize=13, fontweight="bold")
    ax2.set_ylabel("COP", fontsize=13, fontweight="bold")
    # Remove in-plot title for unified look
    # ax2.set_title("COP curves – all sizes and supply temps", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.7)
    ax2.legend(fontsize=13, loc="upper left", frameon=False)
    ax2.tick_params(axis='x', labelsize=11)
    ax2.tick_params(axis='y', labelsize=11)
    st.pyplot(fig2)

with col_eff:
    st.subheader("🔧 Gas Boiler Efficiency – Aggregated Datasheet Evaluation")
    # ...existing gas boiler efficiency code...
    fig_eff, ax_eff = plt.subplots(figsize=(6, 2.5))
    eta_high = 0.889      # Operating extreme (high)
    eta_low = 0.987       # Operating extreme (low)
    etas_min = 0.92       # Seasonal efficiency minimum
    etas_max = 0.94       # Seasonal efficiency maximum
    etas_median = 0.93    # Seasonal efficiency median
    # Plot ranges
    ax_eff.vlines(x=[eta_high, eta_low], ymin=0, ymax=1, colors='coral', 
                  linestyles='--', linewidth=1.5, label='Operating Range (η: 0.889–0.987)')
    ax_eff.fill_betweenx([0, 1], eta_high, eta_low, alpha=0.15, color='coral')
    ax_eff.vlines(x=[etas_min, etas_max], ymin=0, ymax=1, colors='steelblue', 
                  linestyles='-', linewidth=1.5, label='Seasonal Range (η: 0.92–0.94)')
    ax_eff.fill_betweenx([0, 1], etas_min, etas_max, alpha=0.18, color='steelblue')
    ax_eff.vlines(x=[etas_median], ymin=0, ymax=1, colors='darkgreen', 
                  linestyles='-', linewidth=2, label=f'Seasonal Median (η: {etas_median})')
    ax_eff.set_xlim(0.85, 1.00)
    ax_eff.set_ylim(0, 1)
    ax_eff.set_xlabel("Efficiency η (-)", fontsize=11, fontweight='bold')
    # No y-label
    ax_eff.set_yticks([])
    ax_eff.tick_params(axis='x', labelsize=9)
    ax_eff.tick_params(axis='y', labelsize=9)
    ax_eff.grid(True, axis='x', linestyle=':', alpha=0.5)
    # Legend below plot, centered, small font
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    st.pyplot(fig_eff)
    st.write("\n\n\n")
    fig_legend, ax_legend = plt.subplots(figsize=(6, 0.5))
    ax_legend.axis('off')
    handles, labels = ax_eff.get_legend_handles_labels()
    ax_legend.legend(handles, labels, loc='center', fontsize=9, frameon=False, ncol=1)
    st.pyplot(fig_legend)



# ============================================================
# Results Table (moved to bottom)
# ============================================================

# ...existing code...

# Place this at the very end of the file, after all other sections



# ============================================================
# Investment Breakdown (stacked bar) — for currently selected size_class
# ============================================================

# ============================================================
# Gas Boiler Efficiency Visualization
# ============================================================

# ============================================================
# Current Parameters Display
# ============================================================
st.sidebar.subheader("📌 Current Parameters Summary")
st.sidebar.write(f"**Heat Demand:** {Q_heat:,.0f} kWh/year")
st.sidebar.write(f"**Lifetime:** {lifetime} Years")
st.sidebar.write(f"**Electricity Price HP:** {price_hp:.3f} €/kWh")
st.sidebar.write(f"**Gas Price:** {price_gas:.3f} €/kWh")

# ============================================================
# 🌍 ENVIRONMENTAL ANALYSIS: CO2 EMISSIONS COMPARISON
# ============================================================
st.subheader("🌍 Environmental Impact: Annual CO2 Emissions")

# 1. Energy Inputs based on your values (0.95 boiler efficiency and 3.4 HP COP)
# Calculation: Heat Demand / Efficiency = Fuel Input
ann_gas_kwh = Q_heat / COP_gb  # ~21,053 kWh if Q_heat=20000
ann_el_kwh = Q_heat / 3.4      # ~5,882 kWh if Q_heat=20000

# 2. German Emission Factors (kg CO2 per kWh)
ef_gas = 0.2356  # Fixed: Fossil Gas (UBA Germany baseline)
ef_hp_scenarios = {
    "HP (Clean)": 0.147,
    "HP (Average)": 0.326,
    "HP (Dirty)": 0.552
}

# 3. Calculate Emissions (converted to Tonnes)
emissions_gb_tonnes = (ann_gas_kwh * ef_gas) / 1000

hp_labels = []
hp_emissions_vals = []
for label, ef in ef_hp_scenarios.items():
    val = (ann_el_kwh * ef) / 1000
    hp_labels.append(label)
    hp_emissions_vals.append(val)

    


# 5. Explanatory Metrics / Key Findings
col_env, col_env_text = st.columns(2)
savings_vs_dirty = emissions_gb_tonnes - max(hp_emissions_vals)

with col_env:
    fig_env, ax_env = plt.subplots(figsize=(10, 5))
    bars_hp = ax_env.bar(hp_labels, hp_emissions_vals, color='#2ecc71', alpha=0.8, label='Heat Pump Scenarios')
    ax_env.axhline(y=emissions_gb_tonnes, color='#e74c3c', linestyle='--', linewidth=3, 
                   label=f'Gas Boiler Baseline ({emissions_gb_tonnes:.2f}t)')
    ax_env.set_ylabel("Annual CO2 Emissions (Tonnes)", fontsize=15, fontweight='bold')
    ax_env.tick_params(axis='x', labelsize=11)
    ax_env.tick_params(axis='y', labelsize=11)
    # Remove in-plot title for unified look
    ax_env.set_title(f"Annual CO2 Footprint for {Q_heat:,} kWh Heat Demand", fontsize=14, pad=15)
    ax_env.set_ylim(0, max(emissions_gb_tonnes, max(hp_emissions_vals)) * 1.3)
    ax_env.legend(fontsize=13, loc='upper left', frameon=False)
    ax_env.grid(axis='y', linestyle=':', alpha=0.6)
    for bar in bars_hp:
        yval = bar.get_height()
        ax_env.text(bar.get_x() + bar.get_width()/2, yval + 0.1, f"{yval:.2f}t", 
                    ha='center', va='bottom', fontweight='bold', color='#27ae60', fontsize=9)
    ax_env.tick_params(axis='x', labelsize=11)
    ax_env.tick_params(axis='y', labelsize=11)
    st.pyplot(fig_env)

with col_env_text:
    st.markdown(f"""
    <div style='margin-bottom: 1.2em; padding: 1em; background: #ffeaea; border-radius: 8px;'>
        <b style='color:#e74c3c;'>Gas Boiler Baseline: ~{emissions_gb_tonnes:.2f} Tonnes</b><br>
        <span style='color:#e74c3c;'>Fossil gas has a fixed carbon content. Emissions stay high regardless of season.</span>
    </div>
    <div style='margin-bottom: 1.2em; padding: 1em; background: #eafaf1; border-radius: 8px;'>
        <b style='color:#27ae60;'>HP Max Saving (Summer): {emissions_gb_tonnes - min(hp_emissions_vals):.2f} Tonnes</b><br>
        <span style='color:#27ae60;'>Maximum reduction in CO₂ emissions with heat pump operation in summer.<br>Even in 'Dirty' winter conditions, the Heat Pump reduces emissions by <b>{savings_vs_dirty:.2f} tonnes</b> per year.</span>
    </div>
    """, unsafe_allow_html=True)


