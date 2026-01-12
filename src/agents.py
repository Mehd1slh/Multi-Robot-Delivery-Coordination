import mesa
import random
import heapq

# Battery States
BATTERY_CAPACITY = 100
BATTERY_DRAIN_MOVE = 1
BATTERY_DRAIN_IDLE = 0.1
CHARGE_RATE = 100
LOW_BATTERY_THRESHOLD = 25
RECOVERY_TIME = 40 

# Robot States
STATE_IDLE = "IDLE"
STATE_TO_PICKUP = "TO_PICKUP"
STATE_TO_DELIVER = "TO_DELIVER"
STATE_CHARGING = "CHARGING"
STATE_TO_CHARGE = "TO_CHARGE"
STATE_FAILED = "FAILED"

# Robot & Package Constants
ROBOT_CAPACITIES = [20, 30, 40]
MIN_PACKAGE_WEIGHT = 5
MAX_PACKAGE_WEIGHT = 40

# color palette for active orders
VISUALIZATION_COLORS = [
    "#00FFFF", "#FF00FF", "#FF1493", "#32CD32", "#008080", 
    "#000080", "#800000", "#808000", "#FFD700", "#4B0082"
]

class Order:
    def __init__(self, order_id, pickup_pos, dropoff_pos, weight):
        self.order_id = order_id
        self.weight = weight
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
        self.previous_state = None
        self.current_order = None
        self.orders_completed = 0
        self.distance_traveled = 0
        self.failure_timer = 0
        self.repairs_triggered = 0
        self.capacity = random.choice(ROBOT_CAPACITIES)

    def step(self):
        # If failed, wait for recovery
        if self.state == STATE_FAILED:
            self.failure_timer -= 1
            if self.failure_timer <= 0:
                print(f"✅ Robot {self.unique_id} RECOVERED! Back to work.")
                self.state = STATE_IDLE
                self.battery = BATTERY_CAPACITY
            return

        self.update_battery()
        
        # Check for battery death
        if self.battery <= 0 and self.state != STATE_FAILED:
            self.trigger_failure()
            return
        
        # Low Battery Logic - preserve current order
        if self.battery < LOW_BATTERY_THRESHOLD and self.state not in [STATE_CHARGING, STATE_TO_CHARGE, STATE_FAILED]:
            if self.previous_state is None:
                self.previous_state = self.state if self.state in [STATE_TO_PICKUP, STATE_TO_DELIVER] else STATE_IDLE
            self.state = STATE_TO_CHARGE
            print(f"🪫 Robot {self.unique_id} charging. Holding Order ID: {self.current_order.order_id if self.current_order else 'None'}")
                
        # STATE MACHINE 
        if self.state == STATE_TO_PICKUP:
            if self.current_order:
                target_access = self.get_access_point(self.current_order.pickup_pos)
                if target_access:
                    self.move_towards(target_access)
                    if self.pos == target_access:
                        self.reset_shelf_color(self.current_order.pickup_pos)
                        self.state = STATE_TO_DELIVER
                        print(f"📦 Robot {self.unique_id} picked up order {self.current_order.order_id}")

        elif self.state == STATE_TO_DELIVER:
            if self.current_order:
                target_access = self.get_access_point(self.current_order.dropoff_pos)
                if target_access:
                    self.move_towards(target_access)
                    if self.pos == target_access:
                        self.complete_order()
            else:
                print(f"⚠️ Robot {self.unique_id} was in DELIVER state but current_order was missing!")
                self.state = STATE_IDLE

        elif self.state == STATE_TO_CHARGE:
            target = self.get_nearest_charger()
            self.move_towards(target)
            if self.pos == target:
                self.state = STATE_CHARGING

        elif self.state == STATE_CHARGING:
            self.charge()
            if self.battery == BATTERY_CAPACITY:
                self.vacate_station()
            
        elif self.state == STATE_IDLE:
            if self.model.coordination_type == "greedy":
                self.behavior_greedy()

    def trigger_failure(self):
        print(f"💥 Robot {self.unique_id} FAILED at {self.pos}! State was: {self.state}")
        old_state = self.state
        self.state = STATE_FAILED
        self.failure_timer = RECOVERY_TIME
        self.repairs_triggered += 1
        if self.current_order:
            self.model.order_manager.handle_robot_failure(self, old_state)
    
    def vacate_station(self):
        """Finds the nearest walkable cell that isn't a charging station to unblock the queue."""
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        moved = False
        
        for neighbor in neighbors:
            cell_contents = self.model.grid.get_cell_list_contents(neighbor)
            is_station = any(isinstance(c, ChargingStationAgent) for c in cell_contents)
            if not is_station and self.model.is_walkable(neighbor):
                self.model.grid.move_agent(self, neighbor)
                moved = True
                break
        
        if not moved:
            print(f"⚠️ Robot {self.unique_id} cannot vacate - no valid neighbor!")
        
        # Resume previous task if exists
        if hasattr(self, 'previous_state') and self.previous_state:
            self.state = self.previous_state
            self.previous_state = None
            print(f"🔄 Robot {self.unique_id} vacated and resumed {self.state} with order {self.current_order.order_id if self.current_order else 'None'}")
        else:
            self.state = STATE_IDLE
            print(f"🔄 Robot {self.unique_id} vacated to IDLE")

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
            print(f"✅ Robot {self.unique_id} completed order {self.current_order.order_id}")
            self.reset_station_color(self.current_order.dropoff_pos)
            self.model.order_manager.report_completion(self.current_order)
            
        self.current_order = None
        self.state = STATE_IDLE
        self.orders_completed += 1

    def get_access_point(self, target_pos):
        x, y = target_pos
        potential_access_points = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
        
        if self.pos in potential_access_points:
            return self.pos
        if self.pos == target_pos:
            return self.pos

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
        """Handle battery charging without changing state - vacate_station handles state resumption"""
        self.battery = min(self.battery + CHARGE_RATE, BATTERY_CAPACITY)
        if self.battery == BATTERY_CAPACITY:
            print(f"⚡ Robot {self.unique_id} fully charged. Will resume upon vacating.")

    def update_battery(self):
        if self.state == STATE_IDLE: 
            self.battery -= BATTERY_DRAIN_IDLE

    def behavior_greedy(self):
        available_orders = self.model.order_manager.get_unassigned_orders()
        if not available_orders: return
        feasible_orders = [o for o in available_orders if o.weight <= self.capacity]
        if not feasible_orders: return

        best_order = min(feasible_orders, key=lambda o: self.calculate_distance(o.pickup_pos))
        if self.model.order_manager.assign_order_specifically(self, best_order):
            self.current_order = best_order
            self.state = STATE_TO_PICKUP

    def calculate_cnp_bid(self, order):
        if self.current_order is not None:
            return -1
        if self.state != STATE_IDLE or self.battery < LOW_BATTERY_THRESHOLD:
            return -1
        if order.weight > self.capacity:
            return -1
        
        dist = self.calculate_distance(order.pickup_pos)
        base_score = (self.battery * 0.5) - (dist * 2.0)
        wasted_space = self.capacity - order.weight
        penalty = wasted_space * 1.0 
        
        return max(0, base_score - penalty)

    def calculate_auction_bid(self, order):
        if self.current_order is not None:
            return float('inf')
        if self.state != STATE_IDLE or self.battery < LOW_BATTERY_THRESHOLD:
            return float('inf')
        if order.weight > self.capacity:
            return float('inf')
        
        dist = self.calculate_distance(order.pickup_pos)
        wasted_space = self.capacity - order.weight
        opportunity_cost = wasted_space * 1.0
        
        return dist + ((BATTERY_CAPACITY - self.battery) * 0.1) + opportunity_cost

    def calculate_distance(self, target):
        return self.manhattan_distance(self.pos, target)


class OrderManagerAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(model)
        self.orders = []
        self.completed_orders = 0
        self.next_order_id = 0

    def step(self):
        if random.random() < self.model.order_rate: 
            self.create_new_order()
            
        unassigned = self.get_unassigned_orders()
        if not unassigned: 
            return
            
        if self.model.coordination_type == "cnp": 
            self.run_cnp_allocation(unassigned)
        elif self.model.coordination_type == "auction": 
            self.run_auction_allocation(unassigned)

    def handle_robot_failure(self, failed_robot, old_state):
        """Handle robot failure and reassign its order"""
        order = failed_robot.current_order
        if not order:
            return
        
        if old_state == "TO_PICKUP":
            # Robot was going to pick up but failed - just release the order
            order.assigned_to = None
            print(f"🔄 Robot {failed_robot.unique_id} failed before pickup. Order {order.order_id} re-released.")
            
        elif old_state in ["TO_DELIVER", "TO_CHARGE"]:
            # Robot had the package (either delivering or going to charge with it)
            # The package is dropped at the failure location
            print(f"🚨 PACKAGE DROPPED! Robot {failed_robot.unique_id} dropped order {order.order_id} at {failed_robot.pos}")
            order.pickup_pos = failed_robot.pos
            order.assigned_to = None
            
            if not str(order.order_id).startswith("RESCUE_"):
                order.order_id = f"RESCUE_{order.order_id}"
        
        else:
            # Any other state (CHARGING, IDLE) - shouldn't have an order, but just in case
            order.assigned_to = None
            print(f"⚠️ Robot {failed_robot.unique_id} failed in unexpected state {old_state} with order {order.order_id}")

        failed_robot.current_order = None
        
        if self.model.coordination_type in ["cnp", "auction"]:
            print(f"🔄 Attempting immediate reallocation of {order.order_id}...")
            unassigned = [order]
            if self.model.coordination_type == "cnp":
                self.run_cnp_allocation(unassigned)
            elif self.model.coordination_type == "auction":
                self.run_auction_allocation(unassigned)

    def create_new_order(self):
        pickup = self.model.get_random_shelf()
        dropoff = self.model.get_random_packing_station()
        if pickup and dropoff:
            weight = random.randint(MIN_PACKAGE_WEIGHT, MAX_PACKAGE_WEIGHT)
            new_order = Order(self.next_order_id, pickup, dropoff, weight)
            self.next_order_id += 1
            self.orders.append(new_order)
            print(f"📋 New order created: ID={new_order.order_id}, Weight={weight}, Pickup={pickup}")
            
            highlight_color = random.choice(VISUALIZATION_COLORS)
            cell_contents_pickup = self.model.grid.get_cell_list_contents(pickup)
            for agent in cell_contents_pickup:
                if isinstance(agent, ShelfAgent): 
                    agent.color = highlight_color
            cell_contents_dropoff = self.model.grid.get_cell_list_contents(dropoff)
            for agent in cell_contents_dropoff:
                if isinstance(agent, PackingStationAgent): 
                    agent.color = highlight_color

    def run_cnp_allocation(self, unassigned_orders):
        idle_robots = [a for a in self.model.schedule.agents 
                      if isinstance(a, RobotAgent) and a.state == STATE_IDLE]
        if not idle_robots: 
            return
            
        for order in unassigned_orders:
            if not idle_robots:
                break
                
            bids = {r: r.calculate_cnp_bid(order) for r in idle_robots}
            valid_bids = {r: s for r, s in bids.items() if s >= 0}
            
            if valid_bids:
                winner = max(valid_bids, key=valid_bids.get)
                if self.assign_order_specifically(winner, order):
                    print(f"🤝 CNP: Robot {winner.unique_id} (cap={winner.capacity}) won order {order.order_id} (weight={order.weight})")
                    idle_robots.remove(winner)

    def run_auction_allocation(self, unassigned_orders):
        idle_robots = [a for a in self.model.schedule.agents 
                      if isinstance(a, RobotAgent) and a.state == STATE_IDLE]
        if not idle_robots: 
            return
            
        for order in unassigned_orders:
            if not idle_robots:
                break
                
            bids = {r: r.calculate_auction_bid(order) for r in idle_robots}
            valid_bids = {r: c for r, c in bids.items() if c != float('inf')}
            
            if valid_bids:
                winner = min(valid_bids, key=valid_bids.get)
                if self.assign_order_specifically(winner, order):
                    print(f"💰 Auction: Robot {winner.unique_id} (cap={winner.capacity}) won order {order.order_id} (weight={order.weight})")
                    idle_robots.remove(winner)

    def assign_order_specifically(self, robot, order):
        if order.assigned_to is None:
            order.assigned_to = robot
            robot.current_order = order
            robot.state = STATE_TO_PICKUP
            return True
        return False

    def get_unassigned_orders(self): 
        return [o for o in self.orders if o.assigned_to is None]
    
    def report_completion(self, order): 
        self.completed_orders += 1
        if order in self.orders:
            self.orders.remove(order)


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