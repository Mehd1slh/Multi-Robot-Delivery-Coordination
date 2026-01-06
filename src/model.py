# model.py
import mesa
import random
from agents import RobotAgent, ShelfAgent, PackingStationAgent, ChargingStationAgent, OrderManagerAgent

GRID_WIDTH = 20
GRID_HEIGHT = 20
NUM_ROBOTS = 3

class WarehouseModel(mesa.Model):
    def __init__(self, coordination_type="cnp", n_robots=NUM_ROBOTS, order_rate=0.08):
        super().__init__()
        self.coordination_type = coordination_type 
        self.num_robots = n_robots
        self.order_rate = order_rate
        self.running = True 
        
        self.grid = mesa.space.MultiGrid(GRID_WIDTH, GRID_HEIGHT, torus=False)
        self.schedule = mesa.time.RandomActivation(self)
        
        self.robot_agents = []
        self.shelves = []
        self.packing_stations = []
        self.charging_stations = []
        
        self._init_warehouse_layout()
        
        self.order_manager = OrderManagerAgent(999, self)
        self.schedule.add(self.order_manager)
        
        self._init_robots()

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Throughput": lambda m: m.order_manager.completed_orders,
                "Total_Repairs": lambda m: sum(r.repairs_triggered for r in m.robot_agents),
                "Conflict_Rate": lambda m: m._get_conflict_rate(),
                "Idle_Time": lambda m: self._get_idle_time()
            },
            agent_reporters={
                "Battery": lambda a: a.battery if isinstance(a, RobotAgent) else None,
                "State": lambda a: a.state if isinstance(a, RobotAgent) else None
            }
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()

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
            # Robots are obstacles if they are at that position
            if isinstance(agent, RobotAgent):
                # If you want active robots to pass each other, keep the original check.
                # To treat FAILED robots as hard obstacles:
                if agent.state == "FAILED":
                    return False
                return False # Keeping your original logic where any robot is an obstacle

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