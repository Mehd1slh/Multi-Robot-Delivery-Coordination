# agents.py
import mesa
import random
import heapq

# ... (Keep constants) ...
BATTERY_CAPACITY = 100
BATTERY_DRAIN_MOVE = 1
BATTERY_DRAIN_IDLE = 0.1
CHARGE_RATE = 5
LOW_BATTERY_THRESHOLD = 20

# Robot States
STATE_IDLE = "IDLE"
STATE_TO_PICKUP = "TO_PICKUP"
STATE_TO_DELIVER = "TO_DELIVER"
STATE_CHARGING = "CHARGING"
STATE_TO_CHARGE = "TO_CHARGE" 

# === Random colors for active orders ===
VISUALIZATION_COLORS = [
    "#00FFFF", "#FF00FF", "#FF1493", "#32CD32", "#008080", 
    "#000080", "#800000", "#808000", "#FFD700", "#4B0082"
]

class Order:
    def __init__(self, order_id, pickup_pos, dropoff_pos):
        self.order_id = order_id
        self.pickup_pos = pickup_pos
        self.dropoff_pos = dropoff_pos
        self.assigned_to = None

class RobotAgent(mesa.Agent):
    def __init__(self, unique_id, model, start_pos):
        super().__init__(model) 
        self.custom_id = unique_id
        self.pos = None
        self.battery = BATTERY_CAPACITY
        self.state = STATE_IDLE
        self.current_order = None
        self.orders_completed = 0
        self.distance_traveled = 0

    def step(self):
        self.update_battery()
        
        # Low Battery Logic
        if self.battery < LOW_BATTERY_THRESHOLD and self.state != STATE_CHARGING and self.state != STATE_TO_CHARGE:
            self.state = STATE_TO_CHARGE
        
        # === STATE MACHINE ===
        if self.state == STATE_TO_PICKUP:
            if self.current_order:
                target_access = self.get_access_point(self.current_order.pickup_pos)
                if target_access:
                    self.move_towards(target_access)
                    if self.pos == target_access:
                        self.reset_shelf_color(self.current_order.pickup_pos)
                        self.state = STATE_TO_DELIVER

        elif self.state == STATE_TO_DELIVER:
            if self.current_order:
                target_access = self.get_access_point(self.current_order.dropoff_pos)
                if target_access:
                    self.move_towards(target_access)
                    if self.pos == target_access:
                        self.complete_order()

        elif self.state == STATE_TO_CHARGE:
            target = self.get_nearest_charger()
            self.move_towards(target)
            if self.pos == target:
                self.state = STATE_CHARGING

        elif self.state == STATE_CHARGING:
            self.charge()
            
        elif self.state == STATE_IDLE:
            if self.model.coordination_type == "greedy":
                self.behavior_greedy()

    def reset_shelf_color(self, pos):
        if self.model.grid.out_of_bounds(pos): return
        cell_contents = self.model.grid.get_cell_list_contents(pos)
        for agent in cell_contents:
            if isinstance(agent, ShelfAgent):
                agent.color = "brown"

    def reset_station_color(self, pos):
        if self.model.grid.out_of_bounds(pos): return
        cell_contents = self.model.grid.get_cell_list_contents(pos)
        for agent in cell_contents:
            if isinstance(agent, PackingStationAgent):
                agent.color = "black"

    def complete_order(self):
        if self.current_order:
            self.reset_station_color(self.current_order.dropoff_pos)
            self.model.order_manager.report_completion(self.current_order)
            
        self.current_order = None
        self.state = STATE_IDLE
        self.orders_completed += 1

    # ... (Keep get_access_point, get_nearest_charger, move_towards, a_star_search, etc.) ...
    def get_access_point(self, target_pos):
        x, y = target_pos
        potential_access_points = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        valid_points = [p for p in potential_access_points if self.model.is_walkable(p)]
        if not valid_points: return None 
        return min(valid_points, key=lambda p: self.manhattan_distance(self.pos, p))

    def get_nearest_charger(self):
        chargers = self.model.charging_stations
        if not chargers: return self.pos
        return min(chargers, key=lambda c: self.manhattan_distance(self.pos, c))

    def move_towards(self, target_pos):
        if self.pos == target_pos: return
        path = self.a_star_search(self.pos, target_pos)
        if path and len(path) > 0:
            next_step = path[0] 
            if self.model.is_walkable(next_step):
                self.model.grid.move_agent(self, next_step)
                self.distance_traveled += 1
                self.battery -= BATTERY_DRAIN_MOVE

    def a_star_search(self, start, goal):
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}
        found_goal = False

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                found_goal = True
                break

            for next_pos in self.get_neighbors(current):
                new_cost = cost_so_far[current] + 1 
                if not self.model.is_walkable(next_pos): continue
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + self.manhattan_distance(next_pos, goal)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current
        
        if found_goal: return self.reconstruct_path(came_from, start, goal)
        return []

    def get_neighbors(self, pos):
        x, y = pos
        candidates = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        valid_neighbors = []
        for (cx, cy) in candidates:
            if not self.model.grid.out_of_bounds((cx, cy)):
                valid_neighbors.append((cx, cy))
        return valid_neighbors

    def reconstruct_path(self, came_from, start, goal):
        current = goal
        path = []
        while current != start:
            path.append(current)
            current = came_from[current]
        path.reverse() 
        return path

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def charge(self):
        self.battery = min(self.battery + CHARGE_RATE, BATTERY_CAPACITY)
        if self.battery == BATTERY_CAPACITY: self.state = STATE_IDLE

    def update_battery(self):
        if self.state == STATE_IDLE: self.battery -= BATTERY_DRAIN_IDLE

    def behavior_greedy(self):
        available_orders = self.model.order_manager.get_unassigned_orders()
        if not available_orders: return
        best_order = min(available_orders, key=lambda o: self.calculate_distance(o.pickup_pos))
        if self.model.order_manager.assign_order_specifically(self, best_order):
            self.current_order = best_order
            self.state = STATE_TO_PICKUP

    def calculate_cnp_bid(self, order):
        if self.state != STATE_IDLE or self.battery < LOW_BATTERY_THRESHOLD: return -1
        dist = self.calculate_distance(order.pickup_pos)
        return max(0, (self.battery * 0.5) - (dist * 2.0))

    def calculate_auction_bid(self, order):
        if self.state != STATE_IDLE or self.battery < LOW_BATTERY_THRESHOLD: return float('inf')
        dist = self.calculate_distance(order.pickup_pos)
        return dist + (BATTERY_CAPACITY - self.battery) * 0.1

    def calculate_distance(self, target):
        return self.manhattan_distance(self.pos, target)

# ... (OrderManagerAgent and Static Agents) ...
class OrderManagerAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(model)
        self.orders = []
        self.completed_orders = 0

    def step(self):
        # === UPDATED: Use dynamic model.order_rate ===
        if random.random() < self.model.order_rate: 
            self.create_new_order()
            
        unassigned = [o for o in self.orders if o.assigned_to is None]
        if not unassigned: return
        if self.model.coordination_type == "cnp": self.run_cnp_allocation(unassigned)
        elif self.model.coordination_type == "auction": self.run_auction_allocation(unassigned)

    def create_new_order(self):
        pickup = self.model.get_random_shelf()
        dropoff = self.model.get_random_packing_station()
        if pickup and dropoff:
            self.orders.append(Order(len(self.orders), pickup, dropoff))
            
            highlight_color = random.choice(VISUALIZATION_COLORS)
            
            cell_contents_pickup = self.model.grid.get_cell_list_contents(pickup)
            for agent in cell_contents_pickup:
                if isinstance(agent, ShelfAgent):
                    agent.color = highlight_color
            
            cell_contents_dropoff = self.model.grid.get_cell_list_contents(dropoff)
            for agent in cell_contents_dropoff:
                if isinstance(agent, PackingStationAgent):
                    agent.color = highlight_color

    # ... (Keep existing allocation methods) ...
    def run_cnp_allocation(self, unassigned_orders):
        idle_robots = [a for a in self.model.schedule.agents if isinstance(a, RobotAgent) and a.state == STATE_IDLE]
        if not idle_robots: return
        for order in unassigned_orders:
            bids = {r: r.calculate_cnp_bid(order) for r in idle_robots}
            valid_bids = {r: s for r, s in bids.items() if s >= 0}
            if valid_bids:
                winner = max(valid_bids, key=valid_bids.get)
                self.assign_order_specifically(winner, order)
                idle_robots.remove(winner)

    def run_auction_allocation(self, unassigned_orders):
        idle_robots = [a for a in self.model.schedule.agents if isinstance(a, RobotAgent) and a.state == STATE_IDLE]
        if not idle_robots: return
        for order in unassigned_orders:
            bids = {r: r.calculate_auction_bid(order) for r in idle_robots}
            valid_bids = {r: c for r, c in bids.items() if c != float('inf')}
            if valid_bids:
                winner = min(valid_bids, key=valid_bids.get)
                self.assign_order_specifically(winner, order)
                idle_robots.remove(winner)

    def assign_order_specifically(self, robot, order):
        if order.assigned_to is None:
            order.assigned_to = robot
            robot.current_order = order
            robot.state = STATE_TO_PICKUP
            return True
        return False

    def get_unassigned_orders(self): return [o for o in self.orders if o.assigned_to is None]
    def report_completion(self, order): self.completed_orders += 1

class ShelfAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(model)
        self.type_name = "Shelf"
        self.color = "brown" 

class PackingStationAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(model)
        self.type_name = "PackingStation"
        self.color = "black" 

class ChargingStationAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(model)
        self.type_name = "ChargingStation"