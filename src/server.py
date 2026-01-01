# server.py
import sys
import os

# Fix path to allow importing local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mesa
from mesa.visualization import SolaraViz, make_space_component, make_plot_component

# Local Imports
from model import WarehouseModel
from agents import RobotAgent, STATE_TO_DELIVER, STATE_TO_PICKUP, STATE_CHARGING, STATE_TO_CHARGE, LOW_BATTERY_THRESHOLD

# ==========================================
# VISUALIZATION LOGIC
# ==========================================

def agent_portrayal(agent):
    if agent is None: return {}
    portrayal = {"size": 50, "marker": "o"}

    if isinstance(agent, RobotAgent):
        if agent.battery < LOW_BATTERY_THRESHOLD:
            portrayal["color"] = "red"
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
        
        # Check for dynamic color
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

# ==========================================
# MODEL PARAMETERS
# ==========================================

model_params = {
    "coordination_type": {
        "type": "Select",
        "value": "greedy",
        "values": ["greedy", "cnp", "auction"],
        "label": "Coordination Mechanism",
    },
    "n_robots": {
        "type": "SliderInt",
        "value": 5,
        "label": "Number of Robots",
        "min": 1,
        "max": 10,
        "step": 1,
    },
    # === UPDATED: Added slider for Order Rate ===
    "order_rate": {
        "type": "SliderFloat",
        "value": 0.1,
        "label": "Order Rate (Prob/Step)",
        "min": 0.0,
        "max": 1.0,
        "step": 0.05,
    }
}

# ==========================================
# SERVER PAGE
# ==========================================

# Initialize with defaults matching model_params
initial_model = WarehouseModel(n_robots=5, order_rate=0.1)

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