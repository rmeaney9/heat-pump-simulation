'''
Computational Methods and Modelling 3 Group Project

Group Members: Lee Wei Yuan, Ronan Meaney , Lucy Paul , Charlotte Cule
'''

''' Purpose: This software simulates a building's heating system and uses the on/off control model to decide when a heat pump should be turned on and off. Because of the program's extreme flexibility, users can alter the start and end dates as well as any potential constants in the initialisation section. For the system-based ODE, the application solves

based on the user-provided input settings and shows the tank's temperature change over time in a graph.

between the dates that have been set

'''

## Importing Modules ##

# Maths and Graph Plotting/Fitting
import statistics #Finding mean of an array
import math #For Maths Functions
import numpy as np
from scipy.optimize import curve_fit # For performing curve fitting (fitting a function to a dataset).
from scipy.integrate import solve_ivp #Solving ODE
import matplotlib.pyplot as plt #Plotting Graph
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # Embeds plot figures into a tkinter GUI
from matplotlib.figure import Figure 

#GUI
from tkcalendar import DateEntry  # Import DateEntry widget for calendar-based date selection in the GUI
from tkinter import messagebox, ttk  # Import messagebox for pop-up messages and ttk for themed widgets
from datetime import datetime  # Import datetime to handle date and time operations
import tkinter as tk  # Import tkinter for building the main GUI framework


# Data Collection/Extraction
import os  # Import for interacting with the operating system (e.g., file paths, environment variables)
from sys import platform  # Import to check the platform (e.g., Windows, macOS, Linux) for compatibility handling
import yaml  # Import to parse YAML files for configuration or input data
from meteostat import Point, Hourly  # Import Meteostat library to fetch weather data for a specific location and time



class HeatPumpSimulationApp:
    def __init__(self):
        # Initialize the main application window
        self.root = tk.Tk()  # Create the main Tkinter window
        self.root.title("Heat Pump Simulation")  # Window Title
        self.root.geometry("1200x800")  # Set the default window size (width x height)

        # Initialize data arrays and variables
        # Dictionary to store user inputs from GUI fields
        self.input_values = {}
    
        # Arrays to store simulation data for analysis
        self.energy_array = []         # Stores energy consumption values during the simulation
        self.cop_array = []            # Stores Coefficient of Performance (COP) values
        self.q_transfer_array = []     # Stores heat transfer data from the heat pump
        self.q_loss_list = []          # Tracks heat loss throughout the simulation
        self.q_load_array = []         # Tracks heat load on the building
        
        # Variables to manage heat pump status and temperature tracking
        self.pump_status = []          # Tracks whether the heat pump is on or off at each timestep
        self.run_temps = []            # Stores the tank temperatures for each simulation run
        self.run_times = []            # Stores the timestamps for each simulation run
        self.dT_ambient_list = []      # Stores differences between indoor and outdoor temperatures
        
        # Simulation settings and file paths
        self.building_number = 3  # Default building number index, representing the third building option (e.g., Industrial Warehouse). 
        # This is used to determine the hot water demand profile and other building-specific parameters.
        self.include_hot_water_demand = tk.BooleanVar(value=False)  # Boolean flag to include/exclude hot water demand in the simulation
        self.yaml_sim_file_path = "inputs.yaml"  # File path for the simulation input YAML file
        self.yaml_cop_file_path = "heat_pump_cop_synthetic_full.yaml"  # File path for the COP data YAML file
        
        # Arrays for hot water demand and total demand tracking
        self.hot_water_demand = []     # Stores the generated hot water demand profile


        # Initialize time settings
        self.total_hours = 24 #Function with only simulation for 24 hours
        self.time_steps = self.total_hours * 60 #Total Time steps of the simulation
        # Create a time array spanning 24 hours, with each step representing one minute
        self.time = np.linspace(0, self.total_hours, self.time_steps) 

        # Initialize GUI elements
        self.gui_entries = {}
        self.create_gui()
        self.load_yaml_inputs()
        self.root.mainloop()

    def create_gui(self):
        # Create main frames for the various inputs/graphs
        self.create_scrollable_canvas()
        self.create_main_frame()
        self.create_datetime_frame()
        self.create_params_frame()
        self.create_building_buttons_frame()
        self.create_graphs_frame()
        self.create_output_frame()
        self.create_hot_water_demand_frame()

    def create_scrollable_canvas(self): #Creating a scrolling feature in the GUI
        self.canvas = tk.Canvas(self.root) # Create a canvas and add a vertical scrollbar
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew") # Place canvas and scrollbar in the main window
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.root.grid_rowconfigure(0, weight=1) # Configure grid weights to allow resizing
        self.root.grid_columnconfigure(0, weight=1)
        self.content_frame = ttk.Frame(self.canvas) # Create a Frame to contain scrollable content inside the canvas
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")# Embed content_frame into the canvas
        self.content_frame.bind("<Configure>", lambda e: self.set_scroll_region()) # Configure scroll region
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel) # Bind mousewheel event to the canvas

    def set_scroll_region(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mousewheel(self, event): #For Mac user
        if platform == "darwin":  # macOS
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        elif platform == "win32":  # Windows
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:  # Other platforms (Linux)
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def create_main_frame(self):
        # Main Frame to group all elements
        self.main_frame = tk.LabelFrame(self.content_frame, text="Main Configuration")
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

    def create_datetime_frame(self):
        # Frame for Start Date and Time
        datetime_frame = tk.LabelFrame(self.main_frame, text="Start Date and Time")
        datetime_frame.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

        # Start Date and Time
        tk.Label(datetime_frame, text="Start Date:").grid(row=0, column=0, sticky="e", padx=2)
        self.start_date = DateEntry(datetime_frame, width=10, year=2024, month=1, day=1, date_pattern="yyyy-mm-dd")
        self.start_date.grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(datetime_frame, text="Start Time:").grid(row=0, column=2, sticky="e", padx=2)
        self.start_hour = ttk.Combobox(datetime_frame, width=5, values=[f"{i:02d}:00" for i in range(24)])
        self.start_hour.grid(row=0, column=3, sticky="w", padx=5)
        self.start_hour.set("00:00")

        # End Date and Time
        tk.Label(datetime_frame, text="End Date:").grid(row=1, column=0, sticky="e", padx=2)
        self.end_date = DateEntry(datetime_frame, width=10, year=2024, month=1, day=2, date_pattern="yyyy-mm-dd")
        self.end_date.grid(row=1, column=1, sticky="w", padx=5)
        tk.Label(datetime_frame, text="End Time:").grid(row=1, column=2, sticky="e", padx=2)
        self.end_hour = ttk.Combobox(datetime_frame, width=5, values=[f"{i:02d}:00" for i in range(24)])
        self.end_hour.grid(row=1, column=3, sticky="w", padx=5)
        self.end_hour.set("00:00")

    def create_params_frame(self): #GUI for parameters input
        params_frame = tk.LabelFrame(self.main_frame, text="Simulation Parameters")
        params_frame.grid(row=0, column=1, sticky="nw", padx=10, pady=10)

        # Fields for simulation parameters. Include only the parameteres that are interchangeable 
        fields = [
            ("Indoor Setpoint Temperature (K):", "indoor_setpoint"),
            ("Wall Area (m²):", "wall_area"),
            ("Wall U-Value (W/m²K):", "wall_u_value"),
            ("Roof Area (m²):", "roof_area"),
            ("Roof U-Value (W/m²K):", "roof_u_value"),
            ("Mass of Water (Kg):", "mass_of_water"),
            ("Heat Pump On Threshold (K):", "on_threshold"),
            ("Heat Pump Off Threshold (K):", "off_threshold"),
            ("Initial Tank Temperature (K):", "initial_tank_temp"),
            ("Heat Loss Coefficient (W/K):", "heat_loss_coefficient"),
            ("Heat Transfer Coefficient (W/m²K):", "heat_transfer_coefficient"),
            ("Fixed Condenser Temperature (K):", "fixed_condenser_temperature_K"),
            ("Tank Length (m):", "tank_length")
        ]

        # Create labeled entries dynamically instead of having to type it all out
        for row, (label_text, name) in enumerate(fields):
            self.create_labeled_entry(params_frame, label_text, row // 2, row % 2, name)


    def create_labeled_entry(self, parent, label_text, row, column, name, width=10):
        label = tk.Label(parent, text=label_text)
        label.grid(row=row, column=column * 2, sticky="w", padx=3, pady=2)
        
        # Create an entry field with specified width
        entry = tk.Entry(parent, width=width)
        entry.grid(row=row, column=column * 2 + 1, padx=3, pady=2)

         # Setting the length of the tank as it isnt in the YAML input file.
        if name == "tank_length":
            entry.insert(0, "1")  # Default value for tank length

        self.gui_entries[name] = entry
        #Frame for the various buttons
    def create_building_buttons_frame(self):
        # Frame for Buttons
        buttons_frame = tk.Frame(self.main_frame)
        buttons_frame.grid(row=0, column=2, sticky="nw", padx=10, pady=10)
        tk.Label(buttons_frame, text="Select Building Configuration:").grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        #Creating a dictionary to store all the 3 building variables
        self.building_configurations = {
             "Library": {
                 "wall_area": "150",
                 "wall_u_value": "0.3",
                 "roof_area": "150",
                 "roof_u_value": "0.23",
                 "mass_of_water": "200",
                 "indoor_setpoint": "293.15",
                 "heat_loss_coefficient": "5",
                 "heat_transfer_coefficient": "300",
                 "off_threshold": "333.15",
                 "tank_length":"0.6",
             },
             "Modern Office Building": {
                 "wall_area": "220",
                 "wall_u_value": "0.2",
                 "roof_area": "170",
                 "roof_u_value": "0.2",
                 "mass_of_water": "220",
                 "indoor_setpoint": "293.15",
                 "heat_loss_coefficient": "2.5",
                 "heat_transfer_coefficient": "250",
                 "off_threshold": "333.15",
                 "tank_length":"0.7",
             },
             "Industrial Warehouse": {
                 "wall_area": "250",
                 "wall_u_value": "0.35",
                 "roof_area": "180",
                 "roof_u_value": "0.45",
                 "mass_of_water": "230",
                 "indoor_setpoint": "293.15",
                 "heat_loss_coefficient": "8",   
                 "heat_transfer_coefficient": "500",
                 "off_threshold": "333.15",
                 "tank_length":"0.7",
             }
        }

        # Dynamically create buttons for each building type
        for i, building_type in enumerate(self.building_configurations.keys()):
            tk.Button(
                buttons_frame,
                text=building_type,
                command=lambda bt=building_type, bn=i: self.apply_building_configuration(bt, bn),
                width=20
            ).grid(row=1, column=i, padx=5, pady=5)

        # Checkbox for hot water demand. Allow the user to select if they want to include hot water demand
        self.hot_water_checkbox = tk.Checkbutton(
            buttons_frame,
            text="Include Hot Water Demand",
            variable=self.include_hot_water_demand,
            onvalue=True,
            offvalue=False
        )
        self.hot_water_checkbox.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        #Resetting values back to the input file values.
        tk.Button(
            buttons_frame,
            text="Default Values",
            command=self.load_yaml_inputs,
            width=20
        ).grid(row=3, column=0, columnspan=1, padx=5, pady=10)

        # Reset Button
        tk.Button(
            buttons_frame,
            text="Clear",
            command=self.reset_everything,
            width=20
        ).grid(row=3, column=2, columnspan=1, padx=5, pady=10)
        
        # Run Simulation Button
        tk.Button(
            buttons_frame,
            text="Run Simulation",
            command=self.run_simulation,
            width=20
        ).grid(row=3, column=1, columnspan=1, padx=5, pady=10)
# Add a label below the Run Simulation button for messages. Condenser mathematically cannot reach 60 deg if it is set to 60
        self.message_label = tk.Label(buttons_frame, text="", fg="red", font=("Arial", 10, "bold"))
        self.message_label.config(text="Fixed condenser temperature must be above 60°C (333.15K)", fg="red")
        self.message_label.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="w")
    def apply_building_configuration(self, building_type, building_number):
        '''  Applies the selected building configuration to the GUI fields.
            - Updates the simulation parameters based on the chosen building type 
            (e.g., Townhall, Modern Office Building, Detached Apartment).
          - Populates the GUI input fields with preset values for the selected building type.
        '''
        self.building_number = building_number
        if building_type in self.building_configurations:
            config = self.building_configurations[building_type]
            for key, value in config.items():
                if key in self.gui_entries:
                    self.gui_entries[key].delete(0, tk.END)
                    self.gui_entries[key].insert(0, value)

    def create_graphs_frame(self):
        '''
        This function defines the structure and layout for the graphs displayed in the application's GUI. 
        The graphs provide visual insights into key metrics of the simulation, including:
            
            1. Coefficient of Performance (COP):
                - COP vs Temperature Difference (ΔT).
                - COP Over Time (hours).

            2. Tank Temperature Dynamics:
                - Temperature vs Time (hours), which is the main graph of the simulation.

        Details:
            - Each graph is created using Matplotlib's `Figure` and embedded into the GUI using `FigureCanvasTkAgg`.
            - The layout includes subplots for COP metrics and a standalone figure for tank temperature.
            - Graph titles, axes labels, and grid lines are customized for readability and clarity.

        
        '''
        # Create a labeled frame for graphs
        self.graphs_frame = tk.LabelFrame(self.content_frame, text="Graphs")  
        # Creates a labeled frame inside `content_frame` titled "Graphs" to group all graph-related elements visually.
        self.graphs_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")  
        # Positions the graphs frame in row 1, column 0, spans 2 columns, with padding, aligned to the left (west).
        
        # Create a figure for COP (Coefficient of Performance) visualization
        self.fig_cop = Figure(figsize=(6, 6))  
        # Creates a figure of size 6x6 inches to hold multiple subplots for COP-related graphs.
        self.fig_cop.subplots_adjust(hspace=0.5)  
        # Adjusts the vertical spacing (hspace) between subplots within the COP figure.
        
        # Create the first subplot for "COP vs Delta T" (Temperature Difference)
        self.ax_cop = self.fig_cop.add_subplot(211)  
        # Adds a subplot in a grid with 2 rows, 1 column, and this is the first subplot (top panel).
        
        # Set title and labels for the first subplot
        self.ax_cop.set_title("COP vs Temperature Difference", fontsize=16, fontweight='bold')  
        # Sets the title of the first subplot to "COP vs Temperature Difference" with bold styling and size 16 font.
        self.ax_cop.set_xlabel(r"Temperature Difference ($\Delta T$ in °C)", fontsize=14)  
        # Sets the x-axis label to "Temperature Difference (ΔT in °C)", using LaTeX formatting for ΔT, with size 14 font.
        self.ax_cop.set_ylabel("COP", fontsize=14)  
        # Sets the y-axis label to "COP" (Coefficient of Performance) with size 14 font.

        # The following graphs follows the same as above 
        
        # Second subplot for COP over time
        self.ax_cop_time = self.fig_cop.add_subplot(212)
        self.ax_cop_time.set_title("COP Over Time", fontweight="bold", fontsize=16)
        self.ax_cop_time.set_xlabel("Time (hours)", fontsize=14)
        self.ax_cop_time.set_ylabel("COP", fontsize=14)

        # Create the canvas and add it to the graphs frame
        self.canvas_cop = FigureCanvasTkAgg(self.fig_cop, master=self.graphs_frame)
        self.canvas_cop.draw()
        self.canvas_cop.get_tk_widget().grid(row=1, column=0, sticky="e", padx=5, pady=5)

        # Create temperature over time figure. MAIN GRAPH
        self.fig_temp = Figure(figsize=(12, 6))
        self.ax_temp_over_time = self.fig_temp.add_subplot(111)
        self.ax_temp_over_time.set_title("Tank Temperature Vs Time", fontsize=16, fontweight="bold")
        self.ax_temp_over_time.set_xlabel("Time (hours)", fontsize=14)
        self.ax_temp_over_time.set_ylabel("Temperature (°C)", fontsize=14)
        self.ax_temp_over_time.grid(True)

        # Create canvas for temperature plot
        self.canvas_temp = FigureCanvasTkAgg(self.fig_temp, master=self.graphs_frame)
        self.canvas_temp.draw()
        self.canvas_temp.get_tk_widget().grid(row=1, column=1, sticky="e", padx=5, pady=5)

    def create_output_frame(self):
        '''
        Defines the structure and layout for displaying performance metrics, including plots and labels, 
        within the application's GUI. The metrics and visualizations include:
            
            1. Energy Metrics:
                - Average energy consumption (kW).
                - Total energy consumption (kWh).

            2. Coefficient of Performance (COP) Metrics:
                - Average COP over the simulation period.

            3. Heat Loss Metrics:
                - Total heat loss from the tank to the environment (kWh).

            4. Hot Water Demand Metrics:
                - Average hot water demand (kWh) for the simulation period.

            5. Graphical Visualizations:
                - Heat Load vs Delta T.
                - Heat Pump Status Over 24 Hours.
                - Hot Water Demand Profile.
        '''
        # Output Frame for performance metrics
        self.output_frame = tk.LabelFrame(self.content_frame, text="Performance Metrics")
        self.output_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nw")

        # Add labels for metrics
        self.add_label(self.output_frame, "Energy Metrics:", 0, 0) # Add a general label for "Energy Metrics" at row 0, column 0
        self.energy_avg_label = self.add_label(self.output_frame, "Average: -- kW", 0, 1)
        self.energy_total_label = self.add_label(self.output_frame, "Total: -- kWh", 0, 2)
        self.cop_avg_label = self.add_label(self.output_frame, "COP Average: --", 1, 0)
        self.heat_loss_avg_label = self.add_label(self.output_frame, "Total Heat Loss: --kWh", 1, 1)
        self.hot_water_avg_label = self.add_label(self.output_frame, "Hot Water Demand Average: -- kWh", 1, 2)

        # Create heat load figure
        self.fig_heat_load = Figure(figsize=(5, 4))  # Create a figure for the heat load graph with dimensions 5x4 inches
        self.ax_heat_load = self.fig_heat_load.add_subplot(111)  # Add a single subplot (1 row, 1 column, first plot)
        
        # Set title and axis labels for the graph
        self.ax_heat_load.set_title("Heat Load vs Delta T", fontsize=12, fontweight="bold")  # Title of the graph
        self.ax_heat_load.set_xlabel("Delta T", fontsize=10)  # Label for the x-axis (temperature difference)
        self.ax_heat_load.set_ylabel("Heat Load", fontsize=10)  # Label for the y-axis (heat load in watts)
        
        # Add grid lines to the graph for better readability
        self.ax_heat_load.grid(True, linestyle="--", alpha=0.5)  # Add a dashed grid with reduced opacity
        
        # Embed the heat load plot into the output frame
        self.canvas_heat_load = FigureCanvasTkAgg(self.fig_heat_load, master=self.output_frame)  # Embed the figure in the GUI
        self.canvas_heat_load.draw()  # Render the figure for display
        self.canvas_heat_load.get_tk_widget().grid(row=3, column=0, padx=5, pady=5, sticky="w")  
        # Place the graph in the output frame at row 3, column 0 with padding and left alignment

        # Create heat pump status figure
        self.fig_hp_status = Figure(figsize=(5, 4))
        self.ax_hp_status = self.fig_hp_status.add_subplot(111)
        self.ax_hp_status.set_title("Heat Pump Status Over 24 Hours", fontsize=12, fontweight="bold")
        self.ax_hp_status.set_xlabel("Time (hours)", fontsize=10)
        self.ax_hp_status.set_ylabel("Heat Pump Status", fontsize=10)
        self.ax_hp_status.grid(True, linestyle="--", alpha=0.5)

        # Embed the heat pump status plot into the output frame
        self.canvas_hp_status = FigureCanvasTkAgg(self.fig_hp_status, master=self.output_frame)
        self.canvas_hp_status.draw()
        self.canvas_hp_status.get_tk_widget().grid(row=3, column=1, padx=5, pady=5, sticky="w")

    def create_hot_water_demand_frame(self):
        # Create Hot Water Demand Frame
        self.hot_water_demand_frame = tk.LabelFrame(self.output_frame, text="Hot Water Demand")
        self.hot_water_demand_frame.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky="nw")
        self.hot_water_demand_frame.grid_remove()  # Hide initially

        # Create hot water demand figure
        self.fig_hot_water = Figure(figsize=(5, 4))
        self.ax_hot_water = self.fig_hot_water.add_subplot(111)
        self.ax_hot_water.set_title("Hot Water Demand Profile", fontsize=12, fontweight="bold")
        self.ax_hot_water.set_xlabel("Time (hours)", fontsize=10)
        self.ax_hot_water.set_ylabel("Hot Water Demand (kW)", fontsize=10)
        self.ax_hot_water.grid(True, linestyle="--", alpha=0.5)

        # Embed the hot water demand plot into the frame
        self.canvas_hot_water = FigureCanvasTkAgg(self.fig_hot_water, master=self.hot_water_demand_frame)
        self.canvas_hot_water.draw()
        self.canvas_hot_water.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky="w")

    def add_label(self, parent, text, row, column):
        # Create a label widget with specified text and bold font style.
        label = tk.Label(parent, text=text, font=("Arial", 10, "bold"))
        # Place the label in the specified row and column of the parent layout, aligned to the left (west).
        label.grid(row=row, column=column, sticky="w")
        # Return the label object for further use if needed.
        return label

    def load_yaml_inputs(self):
        """The code in this part extracts data from yaml files into the GUI fields. This allows us to
        adjust the constants or preset values"""
        try:
            if not os.path.exists(self.yaml_sim_file_path):
                raise FileNotFoundError(f"The file {self.yaml_sim_file_path} was not found.")
            # Open the YAML file and load its contents
            with open(self.yaml_sim_file_path, "r") as input_file:
                inputs_gui = yaml.safe_load(input_file)

            # Mapping of YAML keys to GUI entry names
            #This ensures the data is correctly linked to the corresponding GUI field
            yaml_to_gui_mapping = {
                'building_properties.wall_area.value': 'wall_area',
                'building_properties.wall_U_value.value': 'wall_u_value',
                'building_properties.roof_area.value': 'roof_area',
                'building_properties.roof_U_value.value': 'roof_u_value',
                'hot_water_tank.mass_of_water.value': 'mass_of_water',
                'building_properties.indoor_setpoint_temperature_K.value': 'indoor_setpoint',
                'heat_pump.on_temperature_threshold_K.value': 'on_threshold',
                'heat_pump.off_temperature_threshold_K.value': 'off_threshold',
                'initial_conditions.initial_tank_temperature_K.value': 'initial_tank_temp',
                'hot_water_tank.heat_loss_coefficient.value': 'heat_loss_coefficient',
                'heat_pump.overall_heat_transfer_coefficient.value': 'heat_transfer_coefficient',
                'heat_pump.heat_transfer_area.value': 'heat_transfer_area',
                'heat_pump.fixed_condenser_temperature_K.value': 'fixed_condenser_temperature_K',
                'hot_water_tank.specific_heat_capacity.value': 'specific_heat_capacity',
            }
          # Iterate through the mapping to populate GUI fields and store the input values
            for yaml_key, gui_key in yaml_to_gui_mapping.items():
                value = self.get_nested_value(inputs_gui, yaml_key.split('.'))
                if gui_key in self.gui_entries:
                    self.gui_entries[gui_key].delete(0, tk.END)
                    self.gui_entries[gui_key].insert(0, value)
                # Store all input values regardless of GUI entries
                self.input_values[gui_key] = float(value)
                # Set default tank_length to 1 meter if not in the YAML file
            if 'tank_length' in self.gui_entries:
                self.gui_entries['tank_length'].delete(0, tk.END)
                self.gui_entries['tank_length'].insert(0, "1")
                self.input_values['tank_length'] = 1.0

        except Exception as e:
           messagebox.showerror("Error", f"Failed to load inputs: {e}")

    def get_nested_value(self, data, keys):
        """
        "Fetch a value from a nested dictionary using a list of keys. Returns the value at the specified path or an empty dictionary if any key is missing."
        """
        for key in keys:
            data = data.get(key, {})
        return data
    
    def initialise_tank_params(self):
        # Finding the Real U_loss
        water_volume = float(self.gui_entries['mass_of_water'].get()) / 1000 #density of water is assumed to be 1000kg/m³
        tank_length = float(self.gui_entries['tank_length'].get()) #Gather from the GUI
        # Finding the radius of the water tank
        water_tank_radius = np.sqrt(water_volume/(tank_length*np.pi))
        # Surface area of a cylinder = A=2πrh+2πr²
        tank_area = 2 * np.pi * water_tank_radius * tank_length + 2 * np.pi * water_tank_radius **2
        # Tank area is related to the amount of heat lost in the system
        self.real_U_loss = float(self.gui_entries['heat_loss_coefficient'].get()) * tank_area

    #This function will be played when the run simulation button is pressed
    def run_simulation(self):
        try:
            # Fetch start and end dates
            start_datetime = datetime.strptime(f"{self.start_date.get()} {self.start_hour.get()}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{self.end_date.get()} {self.end_hour.get()}", "%Y-%m-%d %H:%M")

            # Fetch input values from GUI
            self.fetch_input_values()

            # Initialize and run the simulation
            self.reset_simulation_data()
            self.initialise_tank_params()
            self.initialize_simulation(start_datetime, end_datetime)
            self.calculate_metrics()
            self.update_plots()
            self.display_metrics()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def fetch_input_values(self):
        """
            This function retrieves user-inputted values from the GUI fields
            and updates the `self.input_values` dictionary. These values are
            converted to floats for numerical calculations in the simulation.
        """
        self.input_values.update({
            'wall_area': float(self.gui_entries['wall_area'].get()),
            'wall_u_value': float(self.gui_entries['wall_u_value'].get()),
            'roof_area': float(self.gui_entries['roof_area'].get()),
            'roof_u_value': float(self.gui_entries['roof_u_value'].get()),
            'mass_of_water': float(self.gui_entries['mass_of_water'].get()),
            'indoor_setpoint_temperature_K': float(self.gui_entries['indoor_setpoint'].get()),
            'on_temperature_threshold_K': float(self.gui_entries['on_threshold'].get()),
            'off_temperature_threshold_K': float(self.gui_entries['off_threshold'].get()),
            'initial_tank_temperature_K': float(self.gui_entries['initial_tank_temp'].get()),
            'heat_loss_coefficient': float(self.gui_entries['heat_loss_coefficient'].get()),
            'overall_heat_transfer_coefficient': float(self.gui_entries['heat_transfer_coefficient'].get()),
            'fixed_condenser_temperature_K': float(self.gui_entries['fixed_condenser_temperature_K'].get()),
            'tank_length': float(self.gui_entries['tank_length'].get())
        })

    def reset_simulation_data(self):
        """
            Resets the simulation data arrays to ensure a clean state before a new simulation run. 
            - This ensures that no residual data from previous runs interferes with the accuracy and integrity 
            of the current simulation's results.
       """
        self.energy_array.clear()
        self.q_transfer_array.clear()
        self.cop_array.clear()
        self.dT_ambient_list.clear()
        self.pump_status.clear()
        self.q_loss_list.clear()
        self.outdoor_temp_K_array = []
        
    def reset_everything(self):
        """
            Resets all simulation attributes, GUI elements, and figures to their default state.
                - Clears all simulation-related arrays, including persistent settings and configurations.
                - Resets all GUI components and performance graphs to their initial layout and values.
                - Reloads YAML input values to initialize the application with default parameters.

        """
        attributes_to_clear = [
            self.energy_array,self.q_transfer_array,self.cop_array,self.dT_ambient_list,self.pump_status,self.q_loss_list,
            self.q_load_array,self.run_temps,self.run_times,
            ]

        for attr in attributes_to_clear:
            attr.clear()
            
        self.outdoor_temp_K_array = []
        self.ax_cop.clear()
        self.hot_water_demand_frame.grid_remove()
        self.ax_cop_time.clear()
        self.ax_heat_load.clear()
        self.ax_cop.clear()
        self.ax_temp_over_time.clear()
        self.building_number = 3

        # Set inputs yaml values 
        self.load_yaml_inputs()
        
        # Recreate COP figure
        self.fig_cop.clear()
        self.ax_cop = self.fig_cop.add_subplot(211)
        self.ax_cop.set_title("COP vs Temperature Difference", fontsize=16, fontweight='bold')
        self.ax_cop.set_xlabel(r"Temperature Difference ($\Delta T$ in °C)", fontsize=14)  # Add delta and degree symbols
        self.ax_cop.set_ylabel("COP", fontsize=14)
        self.ax_cop.grid(True, linestyle='--', alpha=0.6)
        
        self.ax_cop_time = self.fig_cop.add_subplot(212)
        self.ax_cop_time.set_title("COP Over Time", fontweight="bold", fontsize=16)
        self.ax_cop_time.set_xlabel("Time (hours)", fontsize=14)
        self.ax_cop_time.set_ylabel("COP", fontsize=14)
        self.ax_cop_time.grid(True, linestyle="--", alpha=0.6)
        self.canvas_cop.draw()
        
        # Recreate Temperature figure
        self.fig_temp.clear()
        self.ax_temp_over_time = self.fig_temp.add_subplot(111)
        self.ax_temp_over_time.set_title("Tank Temperature Vs Time", fontsize=16, fontweight="bold")
        self.ax_temp_over_time.set_xlabel("Time (hours)", fontsize=14)
        self.ax_temp_over_time.set_ylabel("Temperature (°C)", fontsize=14)
        self.ax_temp_over_time.grid(True, linestyle="--", alpha=0.5)
        self.canvas_temp.draw()
        
        # Recreate Heat Load figure
        self.fig_heat_load.clear()
        self.ax_heat_load = self.fig_heat_load.add_subplot(111)
        self.ax_heat_load.set_title("Heat Load vs ΔT", fontsize=16, fontweight="bold")
        self.ax_heat_load.set_xlabel("ΔT (K)", fontsize=14)
        self.ax_heat_load.set_ylabel("Heat Load (W)", fontsize=14)
        self.ax_heat_load.grid(True, linestyle="--", alpha=0.6)
        self.canvas_heat_load.draw()
        
        # Recreate Heat Pump Status figure
        self.fig_hp_status.clear()
        self.ax_hp_status = self.fig_hp_status.add_subplot(111)
        self.ax_hp_status.set_title("Heat Pump Status Over Time", fontsize=12, fontweight="bold")
        self.ax_hp_status.set_xlabel("Time (hours)")
        self.ax_hp_status.set_ylabel("Heat Pump Status")
        self.ax_hp_status.grid(True)
        self.canvas_hp_status.draw()
        
        # Clear Performance Metrics labels
        self.energy_avg_label.config(text="Average: -- kW")
        self.energy_total_label.config(text="Total: -- kWh")
        self.cop_avg_label.config(text="COP Average: --")
        self.heat_loss_avg_label.config(text="Total Heat Loss: --kWh")
        self.hot_water_avg_label.config(text="Hot Water Demand Average: --kWh")
        self.hot_water_avg_label.grid()  # Ensure it is visible after reset
        
        self.include_hot_water_demand.set(False) #Uncheck tick box
        self.hot_water_demand_frame.grid_remove()
        
    def initialize_simulation(self, start_datetime, end_datetime):
        # Define constants
        self.Pump_Power = 2000  # W
        self.condenserT = 60 + 273.15  # K #Condenser Temperature
        self.steps_each_hour = 30
        self.pump_switch = False  # Start with pump Off
        self.graph_colors = plt.cm.tab10.colors
        
        # Store total simulation time
        self.total_seconds = (end_datetime - start_datetime).total_seconds()
        # Validate that the simulation duration is exactly 24 hours
        if self.total_seconds != 86400:  # 24 hours = 86400 seconds
            messagebox.showerror(
                "Invalid Duration",
                "The simulation requires exactly 24 hours. Please adjust your start and end times."
            )
            raise ValueError("Simulation duration must be exactly 24 hours.") 
        
        CheckingCondenserTemp=float(self.gui_entries['fixed_condenser_temperature_K'].get()) 

        if CheckingCondenserTemp < 333.15:
            messagebox.showerror(
                "Invalid Fixed Condenser Temperature",
                "Fixed condenser temperature must be above 60°C (333.15K)"
            )
            raise ValueError("Simulation Parameters invalid") 
        # Load COP data from the YAML file
        # The file path is specified by 'self.yaml_cop_file_path'
        with open(self.yaml_cop_file_path) as cop_file:
            cop_data = yaml.safe_load(cop_file)  # Parse the YAML file into a Python dictionary

        # Extract the noisy COP values from the loaded data
        # 'COP_noisy' contains the Coefficient of Performance values from the dataset
        self.COPData = [entry['COP_noisy'] for entry in cop_data['heat_pump_cop_data']]

        # Extract the corresponding outdoor temperatures (in °C) from the dataset
        # These temperatures are needed to analyze the relationship between outdoor conditions and COP
        outdoor_temps = [entry['outdoor_temp_C'] for entry in cop_data['heat_pump_cop_data']]
        
        #Finding Temperature Difference between condenser and outside temp
        self.deltaT_array = [self.condenserT - (temp + 273.15) for temp in outdoor_temps]

        # Fit COP function
        self.A, self.B = curve_fit(self.COPFunction, self.deltaT_array, self.COPData)[0]
        
        # Extract weather data
        self.outdoor_temp_K_array = self.extract_weather_data(start_datetime, end_datetime)

        # Calculate Q load values
        self.calculate_q_load_values()

        # Solve ODE
        self.solve_ode(start_datetime, end_datetime)

    ''' Collecting Weather Data'''
    def extract_weather_data(self, start_datetime, end_datetime):
        # Define the location based on longitude and latitude defined at the start
        location = Point(55.9533, -3.1883)  # EDINBURGH
        # Fetch hourly temperature data
        weather_data = Hourly(location, start_datetime, end_datetime)
        weather_data = weather_data.fetch()
        outdoor_temp_list = weather_data['temp'].values #Only need temperature
        # Converting each outdoor temperature (from manufacturer) into a deltaT value and appending to list.
        outdoor_temp_K_array = [temp + 273.15 for temp in outdoor_temp_list]
        return outdoor_temp_K_array
    
    # Function that finds COP based on temperature difference between condenser and outdoors
    def COPFunction(self, delta_T, A, B):
        return A + B / delta_T

    # Determines the Q_load for each outside temperature (T_amb) value entered.
    def find_heat_load(self, TAmb):
        '''The heat load, Q_load is the heat used to heat up the Room/House. 
            It is based on the equation:
            
            Q_load = A_w * U_w * (T_amb - T_sp) + A_r * U_r * (T_amb - T_sp)
            
        where:
            A_w   :  Wall area (m²)
            U_w   :  Wall U-value (W/m²K)
            A_r   :  Roof area (m²)
            U_r   :  Roof U-value (W/m²K)
            T_amb :  Ambient outdoor temperature (K)
            T_sp  :  Indoor setpoint temperature (K)

        Only ambient outdoor temperature varies.
        Q load units will be in Watts (W)
        '''
        wall_area = self.input_values['wall_area']
        wall_u_value = self.input_values['wall_u_value']
        roof_area = self.input_values['roof_area']
        roof_u_value = self.input_values['roof_u_value']
        TSetP = self.input_values['indoor_setpoint_temperature_K']
        Q_load = wall_area * wall_u_value * (TAmb - TSetP) + roof_area * roof_u_value * (TAmb - TSetP)
        return Q_load
    
    # with the outdoor temperature in kelvin this function is used to determine the necessary Q_load.
    def calculate_q_load_values(self):
        self.q_load_array.clear()
        self.dT_ambient_list.clear()
        for TAmb in self.outdoor_temp_K_array:
            Q_load = self.find_heat_load(TAmb)
            dT_ambient = TAmb - self.input_values['indoor_setpoint_temperature_K']
            self.q_load_array.append(Q_load)
            self.dT_ambient_list.append(dT_ambient)

    
    def combined_heat_load(self, t, TAmb):
        '''
        The combined heat load accounts for both the building's heat load (Q_load) and the 
        stochastic hot water demand. It calculates the net heat load based on the following:
            
            1. Building heat load (Q_load): The energy required to maintain the desired indoor
            setpoint temperature (T_sp) considering the ambient temperature (T_amb), wall
            area, roof area, and their respective U-values. Unit : Watts
            
            2. Hot water demand: This is a time-varying component representing the energy
            required to heat water for usage (e.g., showers, taps). It is stochastic and depends
            on the building's usage pattern. Unit : Watts 
            
            3. Net heat load: The total heat demand minus the hot water demand.
            
        Formula:
            Net Heat Load = Q_load - Hot Water Demand (MINUS BECAUSE QLOAD is negative)
                
       '''
        self.hot_water_demand = self.generate_hot_water_demand()
        index = int((t / 3600) * self.time_steps / self.total_hours) % len(self.hot_water_demand)
        Q_load = self.find_heat_load(TAmb)
        return Q_load - self.hot_water_demand[index]
    
    def update_pump_status(self, Temp_tank):
        '''
        The heat pump is turned off when T_tank is higher than the off threshold (T_off),
        and vice versa for turning on the tank.
        
        The heat into the tank (Q_transfer) follows the equation:
            
            if heat pump is on:
                
                Q_transfer = U_cond * A_cond * (T_cond - T_tank)
            
            if heat pump is off:
                
                Q_transfer = 0
            
        '''
        if Temp_tank <= self.input_values['on_temperature_threshold_K']:
            self.pump_switch = True #Turn on heat pump
        elif Temp_tank >= self.input_values['off_temperature_threshold_K']:
            self.pump_switch = False #Turn off heat pump
    #Finding Q_Transfer
    def get_Q_transfer(self, Temp_tank, TAmb):
        '''
        Heat input from the heat pump, Q_hp. We assume that all the 
        heat from the heat pump is transferred into the heat tank (Q_hp = Q_transfer)
                
        where:
            U_cond  :  Overall heat transfer coefficient (W/m²K)
            A_cond  :  Heat transfer area (m²)
            T_cond  :  Fixed temperature of the condenser (K)
            T_tank  :  Temperature of the water in the tank (K)
            
        '''
        self.update_pump_status(Temp_tank) #Determine if pump is on or not
        if self.pump_switch:
            Q_max = self.max_Q_hp(TAmb) # Finding possible maximum Q
            U_cond = self.input_values['overall_heat_transfer_coefficient']
            A_cond = self.input_values['heat_transfer_area']
            #Q Transfer Formula as mention before. Q Transfer is in terms of Watts
            Q_transf = U_cond * A_cond * (self.input_values['fixed_condenser_temperature_K'] - Temp_tank) #Watts
            if Q_transf > Q_max:
                Q_transf = Q_max #Watts
        else:
            Q_transf = 0
        self.q_transfer_array.append(Q_transf)
        return Q_transf
            
        # Find maximum heat output based on current conditions. We set heat pump power as 2000 which is based on the power supply
        # for a typical household. We can determine the maximum heat output with the following equation : Q_max = COP * Pump_power
    def max_Q_hp(self, TAmb):
        COP = self.COPFunction(self.input_values['fixed_condenser_temperature_K'] - TAmb, self.A, self.B)
        Q_max = COP * self.Pump_Power #Watts
        return Q_max

    def get_Q_loss(self, Temp_tank, TAmb):
        #Define heat loss in system to be used in the ODE
        '''Aside from thermal load and supply, the tank also loses heat to the surroundings. '''
        Q_loss = self.real_U_loss * (Temp_tank - TAmb) #Watts
        self.q_loss_list.append(Q_loss) #Store it in an array for the performance metrics calculation later on
        return Q_loss

    def find_T_ambient(self, t):
        hour = int(abs(t) // 3600)# Finds the hour in which the time is taken. Use floor division to get only hour number
        if hour < len(self.outdoor_temp_K_array):# Gives ambient outdoor temperature based on time
            return self.outdoor_temp_K_array[hour]
        else:
            return self.outdoor_temp_K_array[-1]
        
    def tank_ode(self, t, Temp_tank):
        """
        Step 5 combines the supply, extraction, and loss of heat from the Thermal Energy Supply (TES).
        We also take into account heat loss to the surroundings. 
        
        The temperature change in the tank can be modelled with the ODE:
            
            d(T_tank)/dt = (Q_hp + Q_load - Q_loss)/(M_water * c_water)
            
        where:
            M_water :  Mass of water in tank (kg)
            c_water      : Specific heat capacity of water (J/kg·K)

        Note: we add the value of Q_load as it is given as a negative value
            : we use the equation with M_water as M_water is a given input parameter
        """
        # Step 1: Find the ambient temperature at the current time (t).
        TAmb = self.find_T_ambient(t)

        # Step 2: Calculate the heat transferred into the tank by the heat pump (Q_transfer).
        Q_transfer = self.get_Q_transfer(Temp_tank, TAmb)
        
        # Step 3: Compute the heat lost to the surroundings (Q_loss).
        Q_loss = self.get_Q_loss(Temp_tank, TAmb)
        
        # Step 4: Compute the heat load (Q_load), including hot water demand if enabled.
        if self.include_hot_water_demand.get():
                Q_load = self.combined_heat_load(t, TAmb)  # Net heat load (building + hot water demand).
        else:
                Q_load = self.find_heat_load(TAmb)  # Heat load from building only.

        # Step 5: Define constants for water's specific heat capacity and the mass of water in the tank.
        c_water = self.input_values['specific_heat_capacity']  # Specific heat capacity of water (J/kg·K).
        MassWater = self.input_values['mass_of_water']  # Mass of water in the tank (kg).

        # Step 6: Calculate the rate of temperature change using the ODE formula.
        # This considers heat inputs (Q_transfer), heat loads (Q_load), and heat losses (Q_loss).
        dT_tankdt = (Q_transfer + Q_load - Q_loss) / (MassWater * c_water)

        return dT_tankdt

    def solve_ode(self, start_datetime, end_datetime):
        # Solve ODE for tank temperature dynamics over the simulation period.
        # Initial condition for the ODE (starting tank temperature)
        y0 = [self.input_values['initial_tank_temperature_K']]

        ODE_solution = solve_ivp(
            self.tank_ode,  # ODE function
            t_span=(0, self.total_seconds), # Time range (start to end in seconds)
            y0=y0,# Initial condition
            max_step=3600 / self.steps_each_hour # Maximum step size
        )
        # Store results for plotting and analysis
        self.run_times.append(ODE_solution.t)
        self.run_temps.append(ODE_solution.y[0])

# TASK C : PERFORMANCE Metrics
    def calculate_metrics(self):
        # Only calculate metrics for the latest run
        '''
        Calculates key performance metrics for the heating system, including average and total energy consumption, average COP
        , average heat loss, and hot water demand energy (if applicable).

        '''
        # Retrieve the latest tank temperatures and timestamps
        temp_tank_list = self.run_temps[-1]
        time_list = self.run_times[-1]
        # Initialize arrays to store computed data
        energyarray = []  # Stores energy consumption at each timestep
        q_transfer_array = []  # Stores heat transfer data
        cop_array = []  # Tracks COP values
        q_loss_list = []  # Tracks heat loss over time
        pump_status_list = []  # Tracks heat pump on/off status
        pump_switch = False  # Initial pump status
        # Define threshold Temperature for pump control
        on_threshold = math.floor(self.input_values['on_temperature_threshold_K'])
        off_threshold = math.floor(self.input_values['off_temperature_threshold_K'])

        for i in range(len(temp_tank_list)):
            Temp_tank = temp_tank_list[i] #Tank temp at i
            t = time_list[i] #Time at i
            TAmb = self.find_T_ambient(t) #Ambient temperature at t

            # Update pump status
            if round(Temp_tank) <= on_threshold:
                pump_switch = True
            elif round(Temp_tank) >= off_threshold:
                pump_switch = False
            pump_status_list.append(int(pump_switch))

            # Compute Q_transfer
            if pump_switch:
                Q_max = self.max_Q_hp(TAmb)
                U_cond = self.input_values['overall_heat_transfer_coefficient']
                A_cond = self.input_values['heat_transfer_area']
                Q_transf = U_cond * A_cond * (self.input_values['fixed_condenser_temperature_K'] - Temp_tank)
                if Q_transf > Q_max:
                    Q_transf = Q_max #Limit Q_transfer to maximum capacity if necessary
            else:
                Q_transf = 0

            # Compute Q_loss: heat lost to the surroundings
            Q_loss = self.get_Q_loss(Temp_tank, TAmb)

            # Compute COP based on temperature difference
            delta_T = self.input_values['fixed_condenser_temperature_K'] - TAmb
            COP = self.COPFunction(delta_T, self.A, self.B)
            cop_array.append(COP)

            # Compute Energy Consumption
            if COP > 0:
                energy = Q_transf / COP
                energyarray.append(energy)
                
            else:
                energyarray.append(0)
            # Append computed values to respective arrays    
            q_transfer_array.append(Q_transf)
            q_loss_list.append(Q_loss)

         # Store computed data in class attributes
        self.pump_status = pump_status_list
        self.energy_array = energyarray
        self.q_transfer_array = q_transfer_array
        self.cop_array = cop_array
        self.q_loss_list = q_loss_list
        self.time_cop_array = np.array(time_list)

        # Calculate performance metrics
        self.energy_metrics = {
            "average": statistics.fmean(energyarray) / 1000,  # Average energy consumption in kW, computed by finding the mean of `energyarray` (in Watts) and converting to kW.
            "total": sum(energyarray) / (self.steps_each_hour * 1000)  # Total energy consumption in kWh, calculated by summing `energyarray` (in Joules/second), averaging per hour, and converting to kW.
            }
        self.COP_average = sum(cop_array) / len(cop_array)  # Average COP over the simulation
        
        # Compute total heat loss and calculate the average heat loss in kWh
        self.Q_loss_average = sum(q_loss_list) / (1000*self.steps_each_hour)  #in kW
            #`self.Q_loss_average` calculates the average heat loss in kilowatts (kW) by summing `q_loss_list` (J/s),
            #dividing by `self.steps_each_hour` for hourly average, and converting to kW by dividing by 1000.
        if self.include_hot_water_demand.get():
            # Total hot water demand in kWh. Similar calculations to Energy
            self.total_HotWater = (sum(self.hot_water_demand) / 1000)/self.steps_each_hour

    def update_plots(self):
        # Update GUI plots with latest simulation data.
        self.plot_cop_data()
        self.plot_temperature_over_time()
        self.plot_heat_load_over_deltaT()
        self.update_cop_over_time_plot()
        self.update_hot_water_demand_plot()

    def plot_cop_data(self):
        '''
        Plots the Coefficient of Performance (COP) as a function of temperature difference (ΔT).
        Includes data points and the best-fit line.
        '''
        self.ax_cop.clear()
        self.ax_cop.scatter(self.deltaT_array, self.COPData, label="Data Points", color="royalblue", edgecolor="black", s=50)
        x = np.linspace(min(self.deltaT_array), max(self.deltaT_array), 200)
        y = [self.COPFunction(i, self.A, self.B) for i in x]
        self.ax_cop.plot(x, y, label="Best Fit Line", color="darkorange", linewidth=2, linestyle='--')
        self.ax_cop.set_title("COP vs Temperature Difference", fontsize=16, fontweight='bold')
        self.ax_cop.set_xlabel(r"Temperature Difference ($\Delta T$ in °C)", fontsize=14)  # Add delta and degree symbols
        self.ax_cop.set_ylabel("COP", fontsize=14)
        self.ax_cop.grid(True, linestyle='--', alpha=0.6)
        self.ax_cop.legend(fontsize=12, loc="best")
        self.canvas_cop.draw()

    def update_threshold_values_from_GUI(self):
        '''
        Retrieves the user-defined thresholds for heat pump operation from the GUI
        and converts them from Kelvin to Celsius to plot them on the graph.
        '''
        threshold_on = float(self.gui_entries['on_threshold'].get()) - 273.15
        threshold_off = float(self.gui_entries['off_threshold'].get()) - 273.15
        threshold_on_list = [threshold_on] * len(self.run_times)
        threshold_off_list = [threshold_off] * len(self.run_times)
        return threshold_on_list, threshold_off_list

    def plot_temperature_over_time(self):
        '''
        Plots the tank temperature over time for each simulation run.
        Includes temperature thresholds as horizontal lines.
        '''
        self.ax_temp_over_time.clear()
        threshold_on_list, threshold_off_list = self.update_threshold_values_from_GUI()
        #Allow the user to plot as many graph as they want to. Allowing them to compare between 2 different graphs
        for run_index, (time_data, temp_data) in enumerate(zip(self.run_times, self.run_temps)):
            # Plot the temperature over time
            elapsed_hours = time_data / 3600 
            temps_in_celsius = [temp - 273.15 for temp in temp_data]
            color = self.graph_colors[run_index % len(self.graph_colors)] #Pick a different color for next simulation
            label = f'Run {run_index + 1}'
            self.ax_temp_over_time.plot(elapsed_hours, temps_in_celsius, color=color, linewidth=2, label=label)

            # Plot the threshold lines
            threshold_on = threshold_on_list[run_index]
            threshold_off = threshold_off_list[run_index]
            self.ax_temp_over_time.axhline(y=threshold_on, color=color, linestyle='--', alpha=0.8)
            self.ax_temp_over_time.axhline(y=threshold_off, color=color, linestyle='--', alpha=0.8)

        self.ax_temp_over_time.set_title("Tank Temperature Vs Time", fontsize=16, fontweight="bold")
        self.ax_temp_over_time.set_xlabel("Time (hours)", fontsize=14)
        self.ax_temp_over_time.set_ylabel("Temperature (°C)", fontsize=14)
        self.ax_temp_over_time.grid(True, linestyle="--", alpha=0.5)
        # Position the legend on the right side of the graph
        self.ax_temp_over_time.legend(
        fontsize=10, loc="center left", bbox_to_anchor=(1, 0.5)
        )
        self.canvas_temp.draw()

    def plot_heat_load_over_deltaT(self):
        '''
        Plots the heat load of the building as a function of the temperature difference (ΔT).
        '''
        self.ax_heat_load.clear()
        self.ax_heat_load.plot(self.dT_ambient_list, self.q_load_array, label="Heat Load vs ΔT", color="royalblue", linewidth=2)
        self.ax_heat_load.set_title("Heat Load vs ΔT", fontsize=16, fontweight="bold")
        self.ax_heat_load.set_xlabel("ΔT (K)", fontsize=14)
        self.ax_heat_load.set_ylabel("Heat Load (W)", fontsize=14)
        self.ax_heat_load.grid(True, linestyle="--", alpha=0.6)
        self.canvas_heat_load.draw()

    def update_cop_over_time_plot(self):
        '''
        Plots the Coefficient of Performance (COP) as a function of time over the simulation period.
        '''
        self.ax_cop_time.clear()
        time_in_hours = self.time_cop_array / 3600
        self.ax_cop_time.plot(time_in_hours, self.cop_array, label="COP Over Time", color="royalblue", linewidth=2)
        self.ax_cop_time.set_title("COP Over Time", fontweight="bold", fontsize=16)
        self.ax_cop_time.set_xlabel("Time (hours)", fontsize=14)
        self.ax_cop_time.set_ylabel("COP", fontsize=14)
        self.ax_cop_time.grid(True, linestyle="--", alpha=0.6)
        self.ax_cop_time.legend(fontsize=12, loc="best")
        self.canvas_cop.draw()

    def update_hot_water_demand_plot(self):
        '''
        Updates the hot water demand plot based on the generated stochastic demand.
        Hides the plot if hot water demand is not included in the simulation.
        '''
        if self.include_hot_water_demand.get():
            self.hot_water_demand_frame.grid()
            hot_water_demand = self.generate_hot_water_demand()
            time = np.linspace(0, 24, len(hot_water_demand))
            self.ax_hot_water.clear()
            self.ax_hot_water.plot(time, hot_water_demand/1000, label="Stochastic Hot Water Demand", color="blue", linewidth=2)
            self.ax_hot_water.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
            self.ax_hot_water.set_title("Hot Water Demand Profile", fontsize=14, fontweight="bold")
            self.ax_hot_water.set_xlabel("Time (hours)", fontsize=12)
            self.ax_hot_water.set_ylabel("Hot Water Demand (kW)", fontsize=12) #Hot water demand is measured in terms of kWh
            self.ax_hot_water.legend(loc="upper right", fontsize=10, frameon=True, borderpad=1)
            self.canvas_hot_water.draw()
            
        else:
            self.hot_water_demand_frame.grid_remove()

    def generate_hot_water_demand(self):
        '''
        Generates a stochastic hot water demand profile over the simulation period.

        Steps:
            1. Creates a base demand using a normal distribution (in kW).
            2. Ensures demand values are non-negative by clipping to zero.
            3. Applies a bias factor based on a human usage pattern, which depends on the hour of the day
            and the building type (e.g., office, townhall, or apartment).
            4. Combines base demand with the bias to create the final demand profile.
        '''
        #Base demand (in W) using a normal distribution
        # - loc=0.1: Mean demand is 0.1 W
        # - scale=0.05: Standard deviation is 0.05 W
        base_demand = np.random.normal(loc=0.1, scale=0.05, size=self.time_steps)  # (kW)

        # Step 2: Ensure all demand values are non-negative by clipping below-zero values to 0
        base_demand = np.clip(base_demand, 0, None)

        # Step 3: Apply a human usage pattern bias based on hour and building type
        demand_profile = []
        for i in range(self.time_steps):
            hour = (i / 60) % 24  # Convert timestep index to hour of the day
            bias = self.human_usage_pattern(hour, self.building_number)  # Bias factor (unitless multiplier)
            demand_profile.append(base_demand[i] * bias*1000)  # Final demand = base demand × bias

        # Step 4: Return the demand profile as a numpy array (in kW)
        return np.array(demand_profile)

    def human_usage_pattern(self, hour, building_number):
        """
        Parameters:
            hour (float): Hour of the day (0-24). Units: hours.
            building_number (int): Type of building. Options:
                0 = Library
                1 = Modern Office Building
                2 = Industrial Warehouse
                3 = Normal Apartment (We are assuming this)
            int: Bias factor (unitless multiplier) to adjust the base demand profile.
                    """
        if building_number == 1 :  # Modern Office Building & Warehouse
        # Office usage pattern
            if 0 <= hour < 8 or 18 <= hour < 24:
                return 0  # No water demand during off-hours
            elif 12 <= hour < 14:
                return 2.5  # Peak usage during lunch hours
            else:
                return 1  # Moderate usage during working hours
        elif  building_number == 2:  # Modern Office Building & Warehouse
        # Office usage pattern
            if 0 <= hour < 8 or 18 <= hour < 24:
                return 0.5  # Industrial warehouse is operating 24/7
            elif 12 <= hour < 14:
                return 2.5  # Peak usage during lunch hours
            else:
                return 1.25  # Moderate usage during working hours
        elif building_number == 0:  # Library
            # Library usage pattern
            if 0 <= hour < 8 or 18 <= hour < 24:
                return 0  # No water demand during off-hours
            elif 12 <= hour < 14:
                return 2.5  # Peak usage during lunch hours
            else:
                return 1.25  # Moderate usage during working hours

        else:  # Default (Modelling an apartment)
            # Default usage pattern
            if 6 <= hour < 9:
                return 1.4# Peak usage during morning hours (showers, cooking, cleaning)
            elif 18 <= hour < 21:
                return 1.75  # Peak usage during evening hours (showers, cooking, laundry)
            elif 21 <= hour <= 24:
                return 1.05  # Moderate usage during late evening (wrapping up daily activities)
            elif 9 <= hour <= 18:
                return 0.5  # Low usage during daytime (occupants typically out of home)
            else:
                return 0  # Minimal usage during nighttime/off-hours

    def display_metrics(self):
        '''
        Updates and displays performance metrics and plots in the GUI.
           - Displays calculated metrics such as energy consumption, COP average, 
               total heat loss, and hot water demand (if applicable).
            - Updates the heat pump status plot for visualization.
       '''
        self.energy_avg_label.config(text=f"Average: {self.energy_metrics['average']:.2f} kW")
        self.energy_total_label.config(text=f"Total: {self.energy_metrics['total']:.2f} kWh")
        self.cop_avg_label.config(text=f"COP Average: {self.COP_average:.2f}")
        self.heat_loss_avg_label.config(text=f"Total Heat Loss: {self.Q_loss_average:.2f} kW")
        
        if self.include_hot_water_demand.get():
            self.hot_water_avg_label.config(text=f"Hot Water Demand Total: {self.total_HotWater:.2f} kWh")
        else: 
            self.hot_water_avg_label.config(text="Hot Water Demand Average: --kWh")
        # Update Heat Pump Status Plot
        self.ax_hp_status.clear()
        time_in_hours = self.time_cop_array / 3600
        self.ax_hp_status.plot(time_in_hours, self.pump_status)
        self.ax_hp_status.set_title("Heat Pump Status Over Time", fontsize=12, fontweight="bold")
        self.ax_hp_status.set_xlabel("Time (hours)")
        self.ax_hp_status.set_ylabel("Heat Pump Status")
        self.ax_hp_status.grid(True)
        self.canvas_hp_status.draw()

# Entry point to initialize and launch the Heat Pump Simulation Application
if __name__ == "__main__":
    app = HeatPumpSimulationApp()
