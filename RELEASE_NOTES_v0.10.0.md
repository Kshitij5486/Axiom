# Axiom v0.10.0 — Population Atlas

**Released:** 2026-05-23
**Sprint:** 10 of 12
**Days:** 57-59

---

## What Was Built

Sprint 10 adds the Population Atlas — a new screen
giving population-level clinical intelligence across
all 50 patients simultaneously.

---

## Screen 4 — Population Atlas (population.html)

Technology: D3.js v7, pure HTML/CSS

Page header:
  Population Atlas title
  3 stat pills: 12 High Risk, 18 Watch, 20 Stable
  Beige background, full Axiom design system

Tab switcher (pill-shaped):
  Tab 1: Population Heatmap
  Tab 2: Cohort Causal Graph
  Framer-style fade+slide transition on tab switch

---

## Component 1 — Patient Risk Heatmap

50 patients x 5 clinical variables D3 grid.

Variables: Creatinine, Systolic BP, Glucose,
           Heart Rate, SpO2

Risk sections (top to bottom):
  HIGH RISK (12 patients) — red label
  WATCH (18 patients)     — amber label
  STABLE (20 patients)    — green label

Cell colour coding:
  Critical (dev >1.5x range): #C0392B deep red
  Warning (dev 0.8-1.5x):     #D68910 amber
  Normal (in range):           #14b8a6 teal
  Borderline:                  rgba(0,73,83,0.15)
  No data (8% cells):          #F0ECE6 beige

Hover tooltip:
  Patient name + age
  Current value + unit
  Normal range reference
  Trend arrow (rising/falling/stable)
  Mini D3 sparkline (last 8 readings)
  150ms fade-in spring animation

Sort controls:
  Risk Score (default)
  Survival Probability
  Age
  Diagnosis Group
  Sorts within risk sections only

Patient name labels on left axis.
Section counts in section labels.

---

## Component 2 — Cohort Causal Graph

D3 force simulation, 15 nodes, 22 edges.
Averaged causal structure across 50 patients.

Nodes (15):
  Labs:         Creatinine, Glucose, HbA1c, eGFR, CRP
  Vitals:       BP Systolic, BP Diastolic, HR, SpO2
  Demographics: Age, BMI
  Drugs:        Insulin, Metformin, Lisinopril, Furosemide

Node colours:
  Drug:         rgba(168,85,247,0.15) purple
  Vital:        rgba(0,73,83,0.12) teal
  Lab:          rgba(20,184,166,0.12) teal lighter
  Demographic:  rgba(148,163,184,0.12) grey

Edge encoding:
  Thickness:    effectSize * 5px
  Teal #004953: prevalence >0.8 (consistent)
  Amber #D68910: prevalence 0.4-0.8 (mixed)
  Grey:          prevalence <0.4 (weak)
  Solid:         positive direction
  Dashed:        negative direction
  Arrowheads:    colour-matched markers

Interactions:
  Drag nodes:   D3 drag, reheat simulation
  Hover node:   scale up, stroke thickens
  Click node:   side panel with connections + bars
  Hover edge:   tooltip (source→target, effect, prevalence, direction)
  Labels toggle: show/hide node labels
  Animate:       flowing dash animation on negative edges
  Prevalence slider: filter edges below threshold
    - Filtered edges fade to opacity 0
    - Isolated nodes fade to opacity 0.3
    - Edge counter updates live

Stats row (3 cards):
  Total nodes, Visible edges, Avg effect size

API connection:
  GraphQL port 4000 (primary)
  Demo data fallback (offline)

---

## Navigation

4-screen bottom nav on ALL pages:
  Dashboard, Causal Graph, Counterfactual, Population
  Population button added to dashboard, causal_graph,
  counterfactual pages

---

## Test Summary

| Day | Feature              | Tests | Pass |
|-----|----------------------|-------|------|
| 57  | Scaffold + heatmap   | 9     | 9    |
| 58  | Polish + fixes       | 5     | 5    |
| 59  | GraphQL + release    | 4     | 4    |
| Total                  | 18    | 18   |

---

## Cumulative Test Count

  Backend unit tests:    150
  Dashboard Sprint 8:     17
  Sprint 9 UI:            37
  Sprint 10 UI:           18
  Total:                 222 passed, 0 failed

---

## Next Sprint

Sprint 11 — React Native Mobile App
  Patient list screen
  Vital charts (React Native SVG)
  Push notifications for alerts
  Offline causal graph viewer