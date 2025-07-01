# Heat Pump & Hot Water System Simulation

This project models the performance of an air-to-water heat pump and thermal storage system in residential buildings. It simulates the tank temperature dynamics over time in response to varying outdoor temperatures, building insulation levels, and internal heating demand — all built with Python.

Developed for the **Computational Methods and Modelling 3** course at the University of Edinburgh, this project combines numerical modeling, GUI design, and engineering analysis.

---

## Features

-  ODE-based thermal model** using `scipy.solve_ivp` (RK45)  
-  Dynamic tank temperature simulation** under variable building heat loads  
-  COP curve fitting** using manufacturer data and empirical models  
-  On/off heat pump control logic** with fixed setpoint thresholds  
-  Custom GUI** (Tkinter) for parameter inputs, live plot outputs, and reset functionality  
-  Stochastic modeling** of hot water demand with peak-time bias  
-  Scenario analysis across 3 building types: Office, Warehouse, and Library  
-  Includes engineering report and full YAML-configured inputs

---

## Requirements

Python 3.8+ and the following packages:
- numpy
- scipy
- matplotlib
- PyYAML
- tk
Install them with:

```bash
pip install -r requirements.txt
```
---
## How to Run
```bash
python heat_pump_simulation.py
```

## Output Metrics

- Tank temperature over time
- COP variation vs. outdoor temperature
- Pump cycling frequency
- Energy consumption
- Heat loss from storage

## Model Overview

- COP is modeled using the fitted equation:
$$[ \text{COP} = A + \frac{B}{\Delta T} ]$$
where $$( \Delta T = T_{\text{cond}} - T_{\text{ambient}} )$$
- Hot water tank dynamics solved via ODE:
$$[
\frac{dT_{\text{tank}}}{dt} = \frac{Q_{\text{transfer}} - Q_{\text{load}} - Q_{\text{loss}}}{M \cdot C}
]$$
- Heat pump turns ON when tank temperature drops below 40°C and OFF at 60°C

## ✍️ Author

Ronan Meaney
[LinkedIn](linkedin.com/in/ronan-meaney) | [GitHub](github.com/rmeaney9)
