# model.py
import mesa
import random
from agents import RobotAgent, ShelfAgent, PackingStationAgent, ChargingStationAgent, OrderManagerAgent

GRID_WIDTH = 20
GRID_HEIGHT = 20
NUM_ROBOTS = 3

def compute_gini(model):
    # Calculate fairness based on orders completed per robot
    agent_wealth = [agent.orders_completed for agent in model.robot_agents]
    x = sorted(agent_wealth)
    N = len(model.robot_agents)
    B = sum(x)
    if B == 0: return 0
    return (2 * sum((i + 1) * xi for i, xi in enumerate(x)) - (N + 1) * B) / (N * B)

def get_total_distance(model):
    return sum([agent.distance_traveled for agent in model.robot_agents])

class WarehouseModel(mesa.Model):
    def __init__(self, coordination_type="cnp", n_robots=NUM_ROBOTS, order_rate=0.08, failure_step=-1, map_data=None):
        super().__init__()
        self.coordination_type = coordination_type 
        self.num_robots = n_robots
        self.order_rate = order_rate
        self.running = True
        self.failure_step = failure_step # -1 means no scheduled failure 
        self.schedule = mesa.time.RandomActivation(self)

        # Use dimensions from map or defaults
        self.width = map_data.get("width", GRID_WIDTH) if map_data else GRID_WIDTH
        self.height = map_data.get("height", GRID_HEIGHT) if map_data else GRID_HEIGHT
        
        self.grid = mesa.space.MultiGrid(self.width, self.height, torus=False)
        
        # Initialize lists
        self.robot_agents = []
        self.shelves = []
        self.packing_stations = []
        self.charging_stations = []
        
        # FIXED: Only call ONE layout initialization method
        if map_data:
            self._load_custom_layout(map_data)
        else:
            self._init_warehouse_layout()
        
        self.order_manager = OrderManagerAgent(999, self)
        self.schedule.add(self.order_manager)
        
        self._init_robots()

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Throughput": lambda m: m.order_manager.completed_orders,
                "Conflict_Rate": lambda m: m._get_conflict_rate(),
                "Idle_Time": lambda m: self._get_idle_time(),
                "Total_Distance": get_total_distance,
                "Fairness_Gini": compute_gini
            },
            agent_reporters={
                "Battery": lambda a: a.battery if isinstance(a, RobotAgent) else None,
                "State": lambda a: a.state if isinstance(a, RobotAgent) else None
            }
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()

        # automatic failure injection for scenarios
        if self.schedule.steps == self.failure_step:
            print(f"Scenario Trigger: Injecting failure at step {self.schedule.steps}")
            self.fail_random_robot()

    def _init_warehouse_layout(self):
        # Shelves
        for x in range(3, GRID_WIDTH - 2, 3): 
            for y in range(2, GRID_HEIGHT - 2):
                pos = (x, y)
                self.shelves.append(pos)
                shelf = ShelfAgent(f"Shelf_{x}_{y}", self)
                self.grid.place_agent(shelf, pos)
        
        # Packing Stations
        for y in range(0, GRID_HEIGHT, 2):
            pos = (0, y)
            self.packing_stations.append(pos)
            station = PackingStationAgent(f"Pack_{0}_{y}", self)
            self.grid.place_agent(station, pos)

        # Charging Stations
        self.charging_stations = [(GRID_WIDTH-1, GRID_HEIGHT-1), (GRID_WIDTH-1, 0)]
        for i, pos in enumerate(self.charging_stations):
            charger = ChargingStationAgent(f"Charge_{i}", self)
            self.grid.place_agent(charger, pos)

    def _load_custom_layout(self, data):
        """Places agents based on a dictionary saved by the map editor."""
        for x, y in data["shelves"]:
            shelf = ShelfAgent(f"Shelf_{x}_{y}", self)
            self.grid.place_agent(shelf, (x, y))
            self.shelves.append((x, y))
            
        for x, y in data["packing_stations"]:
            station = PackingStationAgent(f"Pack_{x}_{y}", self)
            self.grid.place_agent(station, (x, y))
            self.packing_stations.append((x, y))
            
        for x, y in data["charging_stations"]:
            charger = ChargingStationAgent(f"Charge_{x}_{y}", self)
            self.grid.place_agent(charger, (x, y))
            self.charging_stations.append((x, y))

    def _init_robots(self):
        for i in range(self.num_robots):
            pos = self.get_random_free_cell()
            robot = RobotAgent(i, self, pos)
            self.grid.place_agent(robot, pos)
            self.schedule.add(robot)
            self.robot_agents.append(robot)

    def is_walkable(self, pos):
        if self.grid.out_of_bounds(pos):
            return False
            
        cell_contents = self.grid.get_cell_list_contents(pos)
        for agent in cell_contents:
            if isinstance(agent, (ShelfAgent, PackingStationAgent)):
                return False
            if isinstance(agent, RobotAgent):
                if agent.state == "FAILED":
                    return False
                return False

        return True

    def fail_random_robot(self):
        active_robots = [r for r in self.robot_agents if r.state != "FAILED"]
        if active_robots:
            robot = self.random.choice(active_robots)
            robot.trigger_failure()

    def _get_conflict_rate(self):
        """Returns count of robots currently failed (acting as obstacles)."""
        return sum(1 for r in self.robot_agents if r.state == "FAILED")

    def _get_idle_time(self):
        """Returns count of robots currently doing nothing."""
        return sum(1 for r in self.robot_agents if r.state == "IDLE")
    
    def get_random_shelf(self):
        return random.choice(self.shelves) if self.shelves else None

    def get_random_packing_station(self):
        return random.choice(self.packing_stations) if self.packing_stations else None

    def get_random_free_cell(self):
        while True:
            x = random.randrange(self.grid.width)
            y = random.randrange(self.grid.height)
            if self.is_walkable((x, y)):
                return (x, y)

    def _get_avg_battery(self):
        batteries = [r.battery for r in self.robot_agents]
        return sum(batteries) / len(batteries) if batteries else 0
    
    def _get_active_robot_count(self):
        return sum(1 for r in self.robot_agents if r.state != "IDLE")