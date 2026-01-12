import pygame
import json
import os

# Define Constants
TILE_TYPES = ["Shelf", "PackingStation", "ChargingStation", "Empty"]
COLORS = {"Shelf": (139, 69, 19), "PackingStation": (0, 0, 0), "ChargingStation": (255, 140, 0), "Empty": (200, 200, 200)}

class MapEditor:
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height
        self.grid = [[ "Empty" for _ in range(height)] for _ in range(width)]
        self.current_selection = "Shelf"
        self.cell_size = 30
        
    def handle_click(self, pos, offset_x, offset_y, right_click=False):
        grid_x = (pos[0] - offset_x) // self.cell_size
        grid_y = (pos[1] - offset_y) // self.cell_size
        
        if 0 <= grid_x < self.width and 0 <= grid_y < self.height:
            if right_click:
                self.grid[grid_x][grid_y] = "Empty"
            else:
                self.grid[grid_x][grid_y] = self.current_selection

    def save_map(self, filename="custom_map.json"):
        data = {
            "width": self.width,
            "height": self.height,
            "shelves": [],
            "packing_stations": [],
            "charging_stations": []
        }
        for x in range(self.width):
            for y in range(self.height):
                tile = self.grid[x][y]
                if tile == "Shelf": data["shelves"].append([x, y])
                elif tile == "PackingStation": data["packing_stations"].append([x, y])
                elif tile == "ChargingStation": data["charging_stations"].append([x, y])
        
        os.makedirs("maps", exist_ok=True)
        with open(f"maps/{filename}", "w") as f:
            json.dump(data, f)
        print(f"Map saved to maps/{filename}")