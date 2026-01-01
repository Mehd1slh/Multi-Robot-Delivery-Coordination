import os
import sys
import subprocess

if __name__ == "__main__":
    # Define the path to your server file relative to this script
    server_file = os.path.join("src", "server.py")

    # Check if file exists just to be safe
    if not os.path.exists(server_file):
        print(f"Error: Could not find {server_file}")
        sys.exit(1)

    print("Launching Multi-Robot Delivery System via Solara...")
    print(f"Target: {server_file}")
    
    # Execute the command 'solara run src/server.py'
    # We use sys.executable to ensure it runs in the current Python environment
    try:
        # On Windows, shell=True is often required to find the 'solara' command
        subprocess.run(["solara", "run", server_file], shell=True, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped.")