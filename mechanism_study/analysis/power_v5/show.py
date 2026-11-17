"""Print compact tables from power_v5_results.csv."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / "power_v5_results.csv", keep_default_na=False, na_values=[""])
pd.set_option("display.width", 250, "display.max_columns", 20, "display.max_rows", 400)

h1 = df[(df.hyp == "H1") & (df["mode"] == "reasoning off") & (df.rule != "-")].copy()
h1["pi"] = h1["pi"].astype(float).round(2)
for scn in ["strong crossover", "moderate crossover", "rule-side only", "no crossover"]:
    s = h1[h1.scenario == scn]
    print(f"\n=== H1 {scn}: unconditional power (testable and p < .05) ===")
    print(s.pivot_table(index=["families_per_type", "repeats", "pi"], columns="rule",
                        values="power_unconditional").round(3).to_string())
print("\n=== H1 strong crossover: probability testable ===")
s = h1[h1.scenario == "strong crossover"]
print(s.pivot_table(index=["families_per_type", "repeats", "pi"], columns="rule", values="p_testable").round(3).to_string())
print("\n=== H1 strong crossover: power if testable ===")
print(s.pivot_table(index=["families_per_type", "repeats", "pi"], columns="rule", values="power_if_testable").round(3).to_string())
print("\n=== H1 mean incorrect first answers per type (strong crossover) ===")
print(s[s.rule.str.startswith("A")].set_index(["families_per_type", "repeats", "pi"])["mean_errors_per_type"].round(1).to_string())
print("\n=== H1 authored drafts power (no gate) ===")
a = h1[h1.rule.str.startswith("A")].pivot_table(index=["families_per_type", "repeats"], columns="scenario",
                                               values="power_authored_drafts").round(3)
print(a.to_string())
print("\n=== H1 reasoning mode and draft ceiling ===")
print(df[(df.hyp == "H1") & ((df["mode"] == "reasoning on") | (df.rule == "-"))][
    ["mode", "scenario", "families_per_type", "repeats", "rule", "p_testable", "power_unconditional", "mean_errors_per_type", "power_authored_drafts"]].round(3).to_string(index=False))
for h in ("H3", "H4", "H2"):
    print(f"\n=== {h} ===")
    print(df[df.hyp == h][["scenario", "families_per_type", "rule", "power_unconditional"]].round(3).to_string(index=False))
