<h1 align="center">Multi-Robot Delivery Coordination </h1>

<p align="center">
  <img src="Capture d'écran 2026-01-11 174001.png" alt="Warehouse Simulation Overview" width="800">
</p>

## 1. Project Overview
This project simulates a **Multi-Agent System (MAS)** for autonomous warehouse logistics using the **Mesa** framework. The research focuses on comparing three coordination mechanisms—**Greedy, Contract Net Protocol (CNP), and Auction**—to evaluate their efficiency and ability to recover from unexpected robot failures.

## 2.  Key Features
* **Three Coordination Modes:** Switch between decentralized Greedy logic, manager-led CNP, or a complex Auction-based cost function.
* **Dynamic Failure & Rescue System:** Automatic detection of robot failures with a specialized "Rescue" protocol that re-allocates dropped packages to active robots.
* **Energy Management:** Advanced battery decay logic based on movement and idle states, featuring autonomous recharging cycles.
* **A StarPathfinding:** Intelligent navigation that treats shelves as obstacles and finds optimal delivery routes.
* **Diverse Fleet:** Robots possess varying weight capacities (20, 30, or 40 units) to test complex allocation logic.

## 3.  Experimental Results & Conclusions
Based on the simulation analysis, we observed the following performance trends:

| Metric | Winner | Conclusion |
| :--- | :--- | :--- |
| **Throughput** | **Greedy** | Best raw speed but suffers from high performance variance. |
| **Fairness** | **CNP** | Lowest Gini coefficient, ensuring equitable workload distribution. |
| **Resilience** | **Auction** | Superior recovery slope post-failure with efficient task re-allocation. |
| **Sustainability** | **Auction** | Highest average battery levels (65.6%) via cost-aware bidding. |

### Key Takeaway
While **Greedy** is effective for raw speed in simple scenarios, **Auction-based coordination** is the superior choice for high-scale, resilient warehouses as it balances energy preservation with reliable recovery from failures.

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Mehd1slh/Multi-Robot-Delivery-Coordination.git
   cd Multi-Robot-Delivery-Coordination
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ````

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ````
## Usage
1. **Running the Benchmark**
   To run comparative analysis of all three coordination mechanisms:
    ```bash
   python benchmark.py --steps 200 --runs 10
    ````
---



<h3 align="center">With profound gratitude for the wisdom and guidance of</h3>
<h2 align="center">DR. AHMADOUN Douae</h2>
<p align="center">A mentor who transforms knowledge into enlightenment and ignites our passion for learning</p>

--- 

<p align="center">
  <img src="Capture d'écran 2026-01-11 175343.png" alt="Project Image" width="600">
</p>
<p align="center">
  <em>15 January, 2026 • Wednesday</em>
</p>



