# Axiom v0.9.0 — 3D Causal Graph + Counterfactual Simulator

**Released:** 2026-05-23
**Sprint:** 9 of 12
**Days:** 50-56

---

## What Was Built

Sprint 9 adds two fully interactive visualization screens
to the Axiom Command Centre, completing the clinical
decision support loop from causal graph to intervention
simulation.

---

## Screen 2 — 3D Causal Graph Explorer (causal_graph.html)

Technology: Three.js r128, CSS2D labels, D3.js

Scene setup:
  Background #F9F7F2 (warm beige, light theme)
  THREE.Fog(#F9F7F2, 80, 200) for depth
  PerspectiveCamera FOV 60 at z=80
  Ambient light 0.6 + Directional light 0.8
  Manual spherical orbit controls

Node rendering:
  MeshPhongMaterial shininess 100
  Emissive glow at intensity 0.18
  BackSide glow sphere child mesh
  Clinical colour coding:
    Labs/Vitals:    #14b8a6 (teal)
    Medications:    #a855f7 (purple)
    Demographics:   #94a3b8 (slate)
    Conditions:     #004953 (brand)
    Other:          #D68910 (amber)
  Centrality-based sizing (1.2x to 3.4x radius)

Edge rendering:
  Parallel lines for thickness (effect size 1-4px)
  Positive effect:  #004953 (teal)
  Negative effect:  #C0392B (red)
  NLP derived:      #f97316 (orange)
  Opacity from CI width (narrow=0.9, wide=0.3)
  Animated particles flowing source to target
  Sine fade on particle opacity

Interactions:
  Hover node:       scale 1.3x, emissive 0.45, label appears
  Click node:       highlight connected edges, show path panel
  Click edge:       show ZK proof + CI + effect in left panel
  Double-click:     camera fly-to with spring easing
  Empty click:      reset all highlights
  Auto-rotate:      speed 0.003, stops on interaction
  Resumes after:    4 seconds inactivity

Overlay panels:
  Left panel:   node/edge details, ZK proof hash, CI bar
  Right panel:  controls, legend, What If mode, drug dropdown
  Bottom panel: time slider with play button
  Patient badge: centered top

API connection:
  1. GraphQL gateway port 4000 (primary)
  2. REST causal engine port 8081 (fallback)
  3. Demo data (offline fallback)

---

## Screen 3 — Counterfactual Simulator (counterfactual.html)

Technology: D3.js v7, CSS animations

Layout:
  Full-width control bar (patient + drug dropdown + Run)
  Split screen: Current State | Simulated State
  Divider line between halves

Left half — Current State:
  3 intervention sliders (SBP, glucose, HR reduction)
  4 metric cards (creatinine, SBP, glucose, HR)
  D3 survival curve (teal, 8 time points)

Right half — Simulated State:
  Skeleton animation during 0.8s API simulation
  4 metric cards with animated count transitions
  Delta badges (green positive, red negative)
  D3 survival curve after intervention (green)

Violin plot (full width):
  1000 Monte Carlo KDE samples
  Current distribution (teal fill)
  Simulated distribution (green dashed)
  Current value line (amber dashed)
  Simulated value line (green dashed)
  Legend with distribution labels

Side effects panel:
  Shows only when intervention has secondary effects
  Causal chain pills in amber
  Effect size per chain

Drug formulary (5 interventions):
  Increase Lisinopril
  Add Furosemide
  Increase Metformin
  Add Aspirin
  Lifestyle Counselling

API connection:
  GraphQL counterfactual mutation (port 4000)
  Demo calculation fallback

---

## Navigation

Bottom nav bar on all 3 screens:
  Dashboard      -> dashboard.html
  Causal Graph   -> causal_graph.html
  Counterfactual -> counterfactual.html
  Active screen highlighted in brand-secondary

---

## Test Summary

| Screen           | Tests | Passed |
|------------------|-------|--------|
| Causal Graph D50 | 10    | 10     |
| Causal Graph D51 | 5     | 5      |
| Causal Graph D52 | 5     | 5      |
| Causal Graph D53 | 5     | 5      |
| Counterfactual   | 8     | 8      |
| GraphQL fallback | 4     | 4      |
| Total            | 37    | 37     |

---

## Service Map (unchanged from v0.8.0)

| Service         | Port  | Sprint |
|-----------------|-------|--------|
| FHIR Adapter    | 8080  | 1      |
| Causal Engine   | 8081  | 2      |
| ZK Service      | 8084  | 3      |
| Federated       | 8085  | 4      |
| Survival        | 8082  | 5      |
| NLP             | 8083  | 6      |
| API Gateway GQL | 4000  | 7      |
| Dashboard       | 3000  | 8      |

---

## Next Sprint

Sprint 10 — Population Atlas
  Population-level causal graph
  Risk stratification heatmap
  Cohort comparison tools