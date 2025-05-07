# controller_log_human.py (Fixed Duration Logging)

import socket
import json
import sys
import csv
import os
import time

# Try importing keyboard, provide instructions if missing
try:
    import keyboard
except ImportError:
    print("\nERROR: The 'keyboard' module is required for this script.")
    print("Please install it using: pip install keyboard")
    print("On Linux/Mac you may need: sudo pip3 install keyboard")
    sys.exit(1)

# Import required classes
from game_state import GameState
from command import Command
from buttons import Buttons
from player import Player

# --- CSV Logging Setup ---
CSV_FILENAME = 'human_sf2_gamedata_p1_5min_1.2.csv'
CSV_HEADER = [
    'timer',
    'p1_id', 'p1_health', 'p1_x', 'p1_y', 'p1_jumping', 'p1_crouching', 'p1_in_move', 'p1_move_id',
    'p2_id', 'p2_health', 'p2_x', 'p2_y', 'p2_jumping', 'p2_crouching', 'p2_in_move', 'p2_move_id',
    'p1_rel_x', 'p1_rel_y', 'p1_facing_opponent', 'p1_health_diff',
    'act_B', 'act_Y', 'act_X', 'act_A', 'act_L', 'act_R',
    'act_Up', 'act_Down', 'act_Left', 'act_Right',
    'act_Select', 'act_Start'
]

# Check if file exists, write header if not
file_exists = os.path.isfile(CSV_FILENAME)
try:
    csv_file = open(CSV_FILENAME, 'a', newline='')
    writer = csv.writer(csv_file)
    if not file_exists:
        writer.writerow(CSV_HEADER)
    print(f"Logging data to: {CSV_FILENAME}")
except IOError as e:
    print(f"Error opening CSV file: {e}")
    sys.exit(1)

# --- Key Mapping ---
KEY_MAPPING = {
    'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
    'z': 'B', 'a': 'Y', 'x': 'A', 's': 'X', 'q': 'L', 'w': 'R',
    'enter': 'start', 'space': 'select'
}

def connect(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        print(f"Attempting to bind to 127.0.0.1:{port}...")
        server_socket.bind(("127.0.0.1", port))
        print(f"Bind successful.")
    except OSError as e:
        print(f"Error binding to port {port}: {e}")
        sys.exit(1)
    print(f"Attempting to listen...")
    server_socket.listen(1)
    print(f"\n--- Waiting for Connection ---")
    print(f"Attempting to accept connection...")
    (client_socket, address) = server_socket.accept()
    print(f"\nCONNECTED to game at {address}!")
    server_socket.close()
    return client_socket

def send(client_socket, command):
    try:
        command_dict = command.object_to_dict()
        pay_load = json.dumps(command_dict).encode()
        client_socket.sendall(pay_load)
    except (BrokenPipeError, OSError) as e:
        print(f"Error sending data: {e}. Connection likely closed.")
        return False
    return True

def receive(client_socket):
    try:
        pay_load = client_socket.recv(4096)
        if not pay_load:
            print("Connection closed by emulator.")
            return None
        input_dict = json.loads(pay_load.decode())
        game_state = GameState(input_dict)
        return game_state
    except (ConnectionResetError, OSError, socket.timeout) as e:
        print(f"Error receiving data: {e}. Connection likely lost or timed out.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from emulator: {e}")
        print(f"Received payload: {pay_load}")
        return None

def get_human_input_buttons():
    human_buttons = Buttons()
    for key, button_attr in KEY_MAPPING.items():
        try:
            if keyboard.is_pressed(key):
                setattr(human_buttons, button_attr, True)
        except Exception as e:
            pass
    return human_buttons

def main():
    if len(sys.argv) != 2 or sys.argv[1] != '1':
         print("\nUsage: python controller.py 1")
         print("The argument '1' specifies that you're controlling player 1")
         sys.exit(1)

    player_to_log = "1"
    port = 9999
    log_duration_seconds = 15 * 60 # 15 minutes

    print("\n--- Human Gameplay Data Logger (15 Minute Duration) ---")
    input("\nPress Enter when you are ready to start listening for the emulator connection...")

    client_socket = None
    frame_count = 0
    start_time = None
    exit_reason = "Unknown"

    try:
        client_socket = connect(port)
        client_socket.settimeout(10.0)

        start_time = time.time()
        print(f"\nLogging started. Will run for {log_duration_seconds / 60:.1f} minutes.")

        current_game_state = None

        # --- Main Loop: Runs for the specified duration ---
        while (time.time() - start_time) < log_duration_seconds:
            # 1. Receive Game State from Emulator
            current_game_state = receive(client_socket)
            if current_game_state is None:
                exit_reason = "Connection Lost/Timeout"
                break

            # 2. Capture Human Input from Keyboard
            human_action_buttons = get_human_input_buttons()

            # 3. Prepare Data Row for CSV
            p1 = current_game_state.player1
            p2 = current_game_state.player2

            # Calculate Added Features
            p1_rel_x = p1.x_coord - p2.x_coord
            p1_rel_y = p1.y_coord - p2.y_coord
            p1_facing_opponent = 1 if p1_rel_x < 0 else 0
            p1_health_diff = p1.health - p2.health

            action_values = [
                int(human_action_buttons.B), int(human_action_buttons.Y), int(human_action_buttons.X),
                int(human_action_buttons.A), int(human_action_buttons.L), int(human_action_buttons.R),
                int(human_action_buttons.up), int(human_action_buttons.down), int(human_action_buttons.left),
                int(human_action_buttons.right), int(human_action_buttons.select), int(human_action_buttons.start)
            ]

            data_row = [
                current_game_state.timer,
                p1.player_id, p1.health, p1.x_coord, p1.y_coord, int(p1.is_jumping), int(p1.is_crouching), int(p1.is_player_in_move), p1.move_id,
                p2.player_id, p2.health, p2.x_coord, p2.y_coord, int(p2.is_jumping), int(p2.is_crouching), int(p2.is_player_in_move), p2.move_id,
                p1_rel_x, p1_rel_y, p1_facing_opponent, p1_health_diff,
            ] + action_values

            # 4. Log Data to CSV
            writer.writerow(data_row)
            frame_count += 1
            
            # Display remaining time and frame count occasionally
            if frame_count % 120 == 0:
                 elapsed = time.time() - start_time
                 remaining = log_duration_seconds - elapsed
                 print(f"Logged frame: {frame_count} | Time remaining: {remaining:.0f}s   ", end='\r')

            # 5. Prepare Command Object to Send Back
            command_to_send = Command()
            command_to_send.player_buttons = human_action_buttons

            # 6. Send Command to Emulator
            if not send(client_socket, command_to_send):
                exit_reason = "Send Failed"
                break

        # Determine exit reason if loop finished normally
        if (time.time() - start_time) >= log_duration_seconds:
             exit_reason = "Time Limit Reached"

    except KeyboardInterrupt:
        print("\nScript interrupted by user (Ctrl+C).")
        exit_reason = "User Interrupted (Ctrl+C)"
    except socket.timeout:
        print("\nSocket operation timed out.")
        exit_reason = "Socket Timeout Exception"
    except Exception as e:
        import traceback
        print(f"\n--- An Unexpected Error Occurred ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        print("Traceback:")
        traceback.print_exc()
        print("------------------------------------")
        exit_reason = f"Unexpected Error: {type(e).__name__}"
    finally:
        # --- Cleanup ---
        print("\nCleaning up...")
        if client_socket:
            print("Closing connection to emulator.")
            client_socket.close()
        if 'csv_file' in locals() and csv_file and not csv_file.closed:
            print(f"Closing CSV file: {CSV_FILENAME}")
            csv_file.close()
            if start_time:
                actual_duration = time.time() - start_time
                print(f"Actual logging duration: {actual_duration:.2f} seconds")
            print(f"Total frames logged: {frame_count}")
            print(f"Exit reason: {exit_reason}")

        # --- Unhook keyboard ---
        try:
            print("Unhooking keyboard...")
            keyboard.unhook_all()
            print("Keyboard unhooked.")
        except Exception as e:
            print(f"Error during keyboard unhook: {e}")

        print("Logger stopped.")


if __name__ == '__main__':
    # --- Admin/sudo check ---
    if os.name != 'nt' and os.geteuid() != 0:
             print("\nWARNING: Script not running as root (sudo).")
             print("Keyboard capture may not work correctly without admin privileges.")
    main()