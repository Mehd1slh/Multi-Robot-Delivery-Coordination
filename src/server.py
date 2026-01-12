# server.py
import sys
import os
import solara

# Fix path to allow importing local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mesa
from mesa.visualization import SolaraViz, make_space_component, make_plot_component

# Local Imports
from model import WarehouseModel
from agents import RobotAgent, STATE_TO_DELIVER, STATE_TO_PICKUP, STATE_CHARGING, STATE_TO_CHARGE, LOW_BATTERY_THRESHOLD


# VISUALIZATION LOGIC

def agent_portrayal(agent):
    if agent is None: return {}
    portrayal = {"size": 50, "marker": "o"}

    if isinstance(agent, RobotAgent):
        # 1. Check FAILED state first and exclusively
        if agent.state == "FAILED": 
            portrayal["color"] = "red"
        
        # 2. Change 'if' to 'elif' here to connect the chain
        elif agent.battery < LOW_BATTERY_THRESHOLD:
            portrayal["color"] = "yellow"
            
        elif agent.state == STATE_TO_DELIVER:
            portrayal["color"] = "green"
        elif agent.state == STATE_TO_PICKUP:
            portrayal["color"] = "blue"
        elif agent.state == STATE_CHARGING:
            portrayal["color"] = "yellow"
        elif agent.state == STATE_TO_CHARGE:
            portrayal["color"] = "orange"
        else:
            portrayal["color"] = "grey"

    elif hasattr(agent, "type_name"):
        portrayal["marker"] = "s" 
        portrayal["size"] = 80
        
        if hasattr(agent, "color"):
            portrayal["color"] = agent.color
        else:
            if agent.type_name == "Shelf":
                portrayal["color"] = "brown"
            elif agent.type_name == "PackingStation":
                portrayal["color"] = "black"
            elif agent.type_name == "ChargingStation":
                portrayal["color"] = "orange"

    return portrayal


# MODEL PARAMETERS

model_params = {
    "coordination_type": {
        "type": "Select",
        "value": "cnp",
        "values": ["greedy", "cnp", "auction"],
        "label": "Coordination Mechanism",
    },
    "n_robots": {
        "type": "SliderInt",
        "value": 3,
        "label": "Number of Robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    "order_rate": {
        "type": "SliderFloat",
        "value": 0.1,
        "label": "Order Rate (Prob/Step)",
        "min": 0.0,
        "max": 1.0,
        "step": 0.05,
    }
}


# SERVER PAGE

# Initialize with defaults matching model_params
initial_model = WarehouseModel(n_robots=3, order_rate=0.08, coordination_type="cnp")

page = SolaraViz(
    model=initial_model,
    components=[
        make_space_component(agent_portrayal),
        make_plot_component({"Throughput": "black"}),
        make_plot_component({"Avg_Battery": "red"}),
        make_plot_component({"Active_Robots": "green"}),
    ],
    model_params=model_params,
    name="Multi-Robot Delivery System"
)

@solara.component
def ManualFaultControls(model):
    with solara.Sidebar(): # This forced the content into the left sidebar
        with solara.Card("Manual Fault Injection"):
            solara.Button(
                label="Fail Random Robot", 
                on_click=model.fail_random_robot, 
                color="error",
                style={"width": "100%"}
            )

# 2. Initialize the model
initial_model = WarehouseModel(n_robots=3, order_rate=0.08, coordination_type="cnp")

# 3. Create the visualization using the standard components list
page = SolaraViz(
    model=initial_model,
    components=[
        make_space_component(agent_portrayal),
        ManualFaultControls,  # Added here, but the Sidebar() wrapper handles placement
        
        # Metric monitoring graphs - keys must match reporters in model.py
        make_plot_component({"Throughput": "black"}),
        make_plot_component({"Total_Distance": "blue"}), 
        make_plot_component({"Conflict_Rate": "red"}),
        make_plot_component({"Fairness_Gini": "purple"}),
    ],
    model_params=model_params,
    name="Multi-Robot Delivery System"
)