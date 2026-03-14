# -*- coding: utf-8 -*-
# SERTS LCOH – Standalone calculation script (no Streamlit)

import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# CORRECTION FACTOR (EN14511 lab → field)
# Applied in cop_interpolated(). Do NOT apply elsewhere.
# ============================================================
CORRECTION_FACTOR = 0.85

# ============================================================
# 1) COP SUPPORT DATA
# Updated: Datenblatt-Mittelwerte aus 20 Herstellerdatasheets (EN14511, A/W35)
# Hersteller: Stiebel Eltron, Vaillant, Wolf, Viessmann, Bosch
# Klassen: small <8kW, medium 8-11kW, large >11kW
# CORRECTION_FACTOR 0.85 wird separat in cop_interpolated() angewendet
# ============================================================
COP_SUPPORT_W35 = {
    "small":  {-7: 2.97, 2: 4.26, 7: 5.26},
    "medium": {-7: 2.97, 2: 4.40, 7: 5.45},
    "large":  {-7: 2.68, 2: 4.06, 7: 5.29},
}

# Temperature bins (load-weighted, sum = 1.0)
TEMP_WEIGHTS = {-7: 0.25, 2: 0.45, 7: 0.30}

SIZE_CLASSES = ["small", "medium", "large"]
SUPPLY_TEMPS = [35, 45, 55]

# ============================================================
# 2) INPUT PARAMETERS
# ============================================================
parameters = {
    # --- Heat demand ---
    "Q_heat":        130 * 120,   # 130 m² × 120 kWh/(m²·a) = 15,600 kWh/a

    # --- System lifetimes ---
    "lifetime_hp":   20,          # [Years]
    "lifetime_gb":   15,          # [Years]
    "discount_rate": 0.05,        # [-]

    # --- Heat pump ---
    "price_hp":      0.38,        # [€/kWh] Destatis H1/2025 baseline
    "CAPEX_hp":      23725,       # [€] medium class, 30% BEG subsidy
    "OPEX_hp":       200,         # [€/year]

    # --- Gas boiler ---
    "price_gas":     0.120,       # [€/kWh] BDEW 2026 EFH baseline
    "CAPEX_gb":      17850,       # [€]
    "OPEX_gb":       350,         # [€/year]
    "COP_gb":        0.88,        # [-] stock average (not new condensing only)

    # --- Emissions & carbon tax ---
    "co2_price_tonne": 55,        # [€/t] BEHG 2025
    "ef_grid":       0.326,       # [kg CO2/kWh] German grid avg (UBA)
    "ef_gas":        0.2356,      # [kg CO2/kWh] fossil gas (UBA)
}

# ============================================================
# 3) COP FUNCTIONS
# ============================================================
def cop_interpolated(T_out, support_points: dict) -> float:
    """
    Interpolate COP for a given outdoor temperature.
    Applies CORRECTION_FACTOR (0.85) to convert EN14511 lab values
    to field-representative values (part-load, defrost, auxiliaries).
    """
    temps = np.array(sorted(support_points.keys()), dtype=float)
    cops  = np.array([support_points[t] for t in temps], dtype=float)
    return float(np.interp(T_out, temps, cops)) * CORRECTION_FACTOR

def cop_carnot(T_hot_C, T_cold_C) -> float:
    """Ideal Carnot COP for given source/sink temperatures (Celsius)."""
    T_hot  = T_hot_C  + 273.15
    T_cold = T_cold_C + 273.15
    return T_hot / (T_hot - T_cold)

def derive_support_points_for_supply_temp(support_W35: dict, T_supply_C: float) -> dict:
    """
    Derive COP support points for a target supply temperature via Carnot scaling.
    W35: uses datasheet support points directly.
    W45/W55: no datasheet data available → derived from W35 via Carnot efficiency.
    """
    if T_supply_C == 35:
        return dict(support_W35)
    derived = {}
    for T_out, cop35 in support_W35.items():
        eta = cop35 / cop_carnot(35, T_out)
        derived[T_out] = eta * cop_carnot(T_supply_C, T_out)
    return derived

def annual_electricity_from_bins(Q_heat_kwh, support_points: dict, weights: dict) -> float:
    """
    Calculate annual electricity consumption via temperature-bin approach.
    E_el = Σ_k (w_k × Q_heat) / COP(T_k)
    Correction factor is applied inside cop_interpolated().
    """
    e_el = 0.0
    for T, w in weights.items():
        cop_T = cop_interpolated(T, support_points)
        e_el += (Q_heat_kwh * w) / cop_T
    return e_el

def effective_annual_cop(support_W35: dict, T_supply: int, weights: dict) -> float:
    """
    Effective annual COP = load-weighted harmonic mean over temperature bins.
    Formula: COP_eff = 1 / Σ(w_k / COP_k)
    Correction factor 0.85 applied inside cop_interpolated().
    """
    support = derive_support_points_for_supply_temp(support_W35, T_supply)
    denom = sum(w / cop_interpolated(T, support) for T, w in weights.items())
    return 1.0 / denom

# ============================================================
# 4) LCOH CALCULATION
# ============================================================
def calculate_lcoh_scenarios(params):
    """Calculate LCOH for all HP scenarios and the gas boiler reference."""
    results   = {}
    r         = params["discount_rate"]
    n_hp      = params["lifetime_hp"]
    n_gb      = params["lifetime_gb"]
    q_heat    = params["Q_heat"]
    co2_price = params["co2_price_tonne"]

    # Discounted heat delivered (normalisation denominator, HP lifetime)
    npv_heat = sum(q_heat / ((1 + r) ** t) for t in range(1, n_hp + 1))

    # --- Gas Boiler ---
    annual_gas_kwh       = q_heat / params["COP_gb"]
    annual_fuel_cost_gb  = annual_gas_kwh * params["price_gas"]
    annual_co2_tonnes_gb = (annual_gas_kwh * params["ef_gas"]) / 1000
    annual_co2_tax_gb    = annual_co2_tonnes_gb * co2_price
    total_annual_cost_gb = annual_fuel_cost_gb + params["OPEX_gb"] + annual_co2_tax_gb
    npv_cost_gb = params["CAPEX_gb"] + sum(
        total_annual_cost_gb / ((1 + r) ** t) for t in range(1, n_gb + 1)
    )
    lcoh_gb = npv_cost_gb / npv_heat

    # --- Heat Pump (all size classes & supply temperatures) ---
    for sc in SIZE_CLASSES:
        support_W35 = COP_SUPPORT_W35[sc]
        for T_supply in SUPPLY_TEMPS:
            support = derive_support_points_for_supply_temp(support_W35, T_supply)
            annual_elec_kwh      = annual_electricity_from_bins(q_heat, support, TEMP_WEIGHTS)
            cop_eff              = effective_annual_cop(support_W35, T_supply, TEMP_WEIGHTS)
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
                "COP_eff":         cop_eff,
            }
    return results

# ============================================================
# 5) PRINT RESULTS
# ============================================================
def print_results(results, params):
    Q = params["Q_heat"]
    print("=" * 75)
    print(f"LCOH RESULTS — Q_heat = {Q:,} kWh/a | η_GB = {params['COP_gb']:.2f} | "
          f"p_el = {params['price_hp']:.2f} €/kWh | p_gas = {params['price_gas']:.3f} €/kWh")
    print("=" * 75)
    print(f"{'Class':>8} | {'Tsink':>6} | {'LCOH_HP':>10} | {'LCOH_GB':>10} | "
          f"{'E_el [kWh/a]':>14} | {'COP_eff':>8} | Result")
    print("-" * 75)
    for sc in SIZE_CLASSES:
        for T_supply in SUPPLY_TEMPS:
            row     = results[(sc, T_supply)]
            lcoh_hp = row["Heat Pump"]
            lcoh_gb = row["Gas Boiler"]
            diff    = abs(lcoh_hp - lcoh_gb)
            verdict = "HP cheaper" if lcoh_hp < lcoh_gb else "GB cheaper"
            print(
                f"{sc:>8} | W{T_supply:<4} | {lcoh_hp:>10.4f} | {lcoh_gb:>10.4f} | "
                f"{row['annual_elec_kwh']:>14,.0f} | {row['COP_eff']:>8.2f} | "
                f"{verdict} by {diff:.4f} €/kWh"
            )
    print("=" * 75)
    print(f"\nGas boiler: {results[('medium',35)]['annual_gas_kwh']:,.0f} kWh_gas/a  "
          f"({Q:,} / {params['COP_gb']:.2f})")
    print(f"HP medium W35: {results[('medium',35)]['annual_elec_kwh']:,.0f} kWh_el/a  "
          f"(COP_eff = {results[('medium',35)]['COP_eff']:.2f})")

# ============================================================
# 6) CUMULATIVE COST FUNCTION (for plots)
# ============================================================
def calculate_cumulative_costs(params, sc, T_supply):
    r   = params["discount_rate"]
    n   = params["lifetime_hp"]
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

# ============================================================
# 7) RUN
# ============================================================
if __name__ == "__main__":
    scenario_results = calculate_lcoh_scenarios(parameters)
    print_results(scenario_results, parameters)
