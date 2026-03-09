# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# 1) INPUT PARAMETERS (same structure as before; COP_hp removed)
# ============================================================
parameters = {
    # --- COMMON PARAMETERS ---
    "Q_heat": 20000,         # [kWh/year]
    "lifetime": 20,          # [Years]
    "discount_rate": 0.05,   # [-]

    # --- HEAT PUMP PARAMETERS ---
    "price_hp": 0.30,        # [€/kWh]
    "CAPEX_hp": 10000,       # [€]
    "OPEX_hp": 200,          # [€/year]

    # --- GAS BOILER PARAMETERS ---
    "price_gas": 0.120,      # [€/kWh]
    "CAPEX_gb": 10000,       # [€]
    "OPEX_gb": 350,          # [€/year]
    "COP_gb": 0.95,          # [-]
}

# ============================================================
# 2) DATA BASIS (replace with your median values!)
# Support points EN14511: A-7/W35, A2/W35, A7/W35
# ============================================================
COP_SUPPORT_W35 = {
    "small":  {-7: 2.80,  2: 3.30,  7: 3.90},  # 5–7 kW
    "medium": {-7: 2.70,  2: 3.20,  7: 3.80},  # 8–10 kW
    "large":  {-7: 2.60,  2: 3.10,  7: 3.70},  # 11–14 kW
}

# Heat-load / temperature bins (sum = 1)
TEMP_WEIGHTS = {-7: 0.25, 2: 0.45, 7: 0.30}

SIZE_CLASSES = ["small", "medium", "large"]
SUPPLY_TEMPS = [35, 45, 55]

# ============================================================
# 3) COP functions (interpolation + supply-temperature scenarios)
# ============================================================
def cop_interpolated(T_out, support_points: dict) -> float:
    temps = np.array(sorted(support_points.keys()), dtype=float)
    cops  = np.array([support_points[t] for t in temps], dtype=float)
    return float(np.interp(T_out, temps, cops))  # clamp outside range


def annual_electricity_from_bins(Q_heat_kwh, support_points: dict, weights: dict) -> float:
    # exact idea: sum Q(T)/COP(T) across temperature bins
    e_el = 0.0
    for T, w in weights.items():
        cop_T = cop_interpolated(T, support_points)
        e_el += (Q_heat_kwh * w) / cop_T
    return e_el


def cop_carnot(T_hot_C, T_cold_C) -> float:
    T_hot = T_hot_C + 273.15
    T_cold = T_cold_C + 273.15
    return T_hot / (T_hot - T_cold)


def derive_support_points_for_supply_temp(support_W35: dict, T_supply_C: float) -> dict:
    # W35 = data-based support points
    if T_supply_C == 35:
        return dict(support_W35)

    # For W45/W55: derive from W35 via Carnot scaling (transparent method)
    derived = {}
    for T_out, cop35 in support_W35.items():
        eta = cop35 / cop_carnot(35, T_out)
        derived[T_out] = eta * cop_carnot(T_supply_C, T_out)
    return derived


# ============================================================
# 4) ORIGINAL-LIKE LCOH FUNCTION (logic similar to original)
#    Extended: multiple scenarios, COP comes from functions above.
# ============================================================
def calculate_lcoh_scenarios(params):
    results = {}

    r = params["discount_rate"]
    n = params["lifetime"]
    q_heat = params["Q_heat"]

    # ---- npv_heat ONCE (similar to original) ----
    npv_heat = 0.0
    for t in range(1, n + 1):
        df = 1 / ((1 + r) ** t)
        npv_heat += q_heat * df

    # ---- Gas: remains constant (similar assumption) ----
    annual_gas_kwh = q_heat / params["COP_gb"]
    annual_fuel_cost_gb = annual_gas_kwh * params["price_gas"]
    total_annual_cost_gb = annual_fuel_cost_gb + params["OPEX_gb"]

    npv_cost_gb = params["CAPEX_gb"]
    for t in range(1, n + 1):
        df = 1 / ((1 + r) ** t)
        npv_cost_gb += total_annual_cost_gb * df

    lcoh_gb = npv_cost_gb / npv_heat

    # ---- Heat pump: now scenarios + COP interpolation ----
    for size_class in SIZE_CLASSES:
        support_W35 = COP_SUPPORT_W35[size_class]

        for T_supply in SUPPLY_TEMPS:
            support = derive_support_points_for_supply_temp(support_W35, T_supply)

            # >>> THIS IS THE ONLY conceptual difference to the original:
            # annual_elec_kwh = q_heat / COP_hp  (old approach)
            # annual_elec_kwh = Sum(Q_bin / COP(T_bin)) (new approach)
            annual_elec_kwh = annual_electricity_from_bins(q_heat, support, TEMP_WEIGHTS)

            annual_fuel_cost_hp = annual_elec_kwh * params["price_hp"]
            total_annual_cost_hp = annual_fuel_cost_hp + params["OPEX_hp"]

            npv_cost_hp = params["CAPEX_hp"]
            for t in range(1, n + 1):
                df = 1 / ((1 + r) ** t)
                npv_cost_hp += total_annual_cost_hp * df

            lcoh_hp = npv_cost_hp / npv_heat

            results[(size_class, T_supply)] = {
                "Heat Pump": lcoh_hp,
                "Gas Boiler": lcoh_gb,
                "annual_elec_kwh": annual_elec_kwh,
                "annual_gas_kwh": annual_gas_kwh,
            }

    return results


# ============================================================
# 5) PRINT RESULTS (similar presentation as before)
# ============================================================
def print_results(results):
    print("-" * 70)
    print("LCOH RESULTS (Germany 2025 Scenario) – scenarios")
    print("-" * 70)

    for size_class in SIZE_CLASSES:
        for T_supply in SUPPLY_TEMPS:
            row = results[(size_class, T_supply)]
            lcoh_hp = row["Heat Pump"]
            lcoh_gb = row["Gas Boiler"]

            diff = abs(lcoh_hp - lcoh_gb)
            if lcoh_hp < lcoh_gb:
                verdict = f">> Heat Pump is cheaper by {diff:.4f} €/kWh"
            else:
                verdict = f">> Gas Boiler is cheaper by {diff:.4f} €/kWh"

            print(f"{size_class:>6} | W{T_supply:<2} | "
                  f"Heat Pump: {lcoh_hp:.4f} €/kWh | "
                  f"Gas Boiler: {lcoh_gb:.4f} €/kWh | "
                  f"HP el: {row['annual_elec_kwh']:.0f} kWh/a")
            print(verdict)

    print("-" * 70)


# ============================================================
# 6) (Deprecated - now using dashboard)
# ============================================================



# ============================================================
# 8) CREATE DASHBOARD (all plots side by side)
# ============================================================
def create_dashboard(scenario_results):
    # Create a figure with subplots (2 rows x 2 columns)
    fig = plt.figure(figsize=(16, 10))
    
    # --- Subplot 1: LCOH Comparison ---
    ax1 = plt.subplot(2, 2, 1)
    labels, hp_vals, gb_vals = [], [], []

    for size_class in SIZE_CLASSES:
        for T_supply in SUPPLY_TEMPS:
            row = scenario_results[(size_class, T_supply)]
            labels.append(f"{size_class}\nW{T_supply}")
            hp_vals.append(row["Heat Pump"])
            gb_vals.append(row["Gas Boiler"])

    x = np.arange(len(labels))
    width = 0.38

    bars_hp = ax1.bar(x - width/2, hp_vals, width, label="Heat Pump")
    bars_gb = ax1.bar(x + width/2, gb_vals, width, label="Gas Boiler")

    ax1.set_ylabel("Levelized Cost of Heat (€/kWh)")
    ax1.set_title("LCOH Comparison: Heat Pump vs Gas Boiler")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.grid(axis="y", linestyle="--", alpha=0.7)
    ax1.legend()

    for bars in (bars_hp, bars_gb):
        for b in bars:
            y = b.get_height()
            ax1.text(b.get_x() + b.get_width()/2, y + 0.001, f"{y:.4f}",
                     ha="center", va="bottom", fontsize=8, fontweight="bold")

# --- Subplot 2: Combined COP curves (all sizes) ---
    ax2 = plt.subplot(2, 2, 2)
    temps_plot = np.linspace(-10, 12, 200)

    # explicit distinct colors for each (size, supply-temp) combination
    # user requested: yellow, red, green, orange, pink, brown, lightblue, purple, blue
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

    # plot every size class and supply temperature on the same axes with assigned colors
    for size_class in SIZE_CLASSES:
        support_base = COP_SUPPORT_W35[size_class]
        for T_supply in SUPPLY_TEMPS:
            support = derive_support_points_for_supply_temp(support_base, T_supply)
            cops = [cop_interpolated(T, support) for T in temps_plot]
            color = color_map.get((size_class, T_supply), "black")
            ax2.plot(temps_plot, cops,
                     label=f"{size_class} W{T_supply}",
                     color=color,
                     linewidth=1.8)
    ax2.set_title("COP curves – all sizes and supply temps")
    ax2.grid(True, linestyle="--", alpha=0.7)
    ax2.legend(fontsize=8)

    # remove the unused subplots 3 and 4 by leaving them blank
    # (the layout stays 2x2, but we only use the top row)
    ax3 = plt.subplot(2, 2, 3)
    ax3.axis('off')
    ax4 = plt.subplot(2, 2, 4)
    ax4.axis('off')

    plt.tight_layout()
    plt.show()


# ============================================================
# 8) RUN
# ============================================================
scenario_results = calculate_lcoh_scenarios(parameters)
print_results(scenario_results)
create_dashboard(scenario_results)
