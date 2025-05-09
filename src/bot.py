from command import Command
import numpy as np
from buttons import Buttons
import tensorflow as tf
from tensorflow.keras.models import load_model
import joblib
import os
import pandas as pd  # Add pandas import

class Bot:

    def __init__(self):
        # Load the trained model and scaler
        # Navigate to the parent directory to access model.h5 and scaler.pkl
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            self.model = load_model(os.path.join(parent_dir, 'model.h5'))
            self.scaler = joblib.load(os.path.join(parent_dir, 'scaler.pkl'))
            self.model_loaded = True
            print("ML model successfully loaded!")
        except Exception as e:
            print(f"Error loading ML model: {e}")
            self.model_loaded = False
        
        # Initialize command and buttons objects
        self.my_command = Command()
        self.buttn = Buttons()

    def fight(self, current_game_state, player):
        # Reset command for this frame
        self.my_command = Command()
        self.buttn = Buttons()
        
        try:
            if self.model_loaded:
                # Extract features from game state
                features = self._extract_features(current_game_state)
                
                # Create a pandas DataFrame with the exact same column names used during training
                # Using the exact column names from gameData.csv
                feature_names = [
                    'timer', 'p1_id', 'p1_health', 'p1_x', 'p1_y', 
                    'p1_jumping', 'p1_crouching', 'p1_in_move', 'p1_move_id',
                    'p2_id', 'p2_health', 'p2_x', 'p2_y', 
                    'p2_jumping', 'p2_crouching', 'p2_in_move', 'p2_move_id',
                    'p1_rel_x', 'p1_rel_y', 'p1_facing_opponent', 'p1_health_diff'
                ]
                features_df = pd.DataFrame([features], columns=feature_names)
                
                # Scale features using the same scaler used during training
                scaled_features = self.scaler.transform(features_df)
                
                # Use the model to predict button presses
                button_presses = self.model.predict(scaled_features, verbose=0)[0]
                
                # Convert predictions to button states (threshold of 0.5 for binary classification)
                button_states = (button_presses > 0.3).astype(int)
                
                # Map predictions to button states
                self._set_button_states(button_states)
            else:
                # Fallback to basic behavior if model isn't loaded
                self._fallback_behavior(current_game_state)
                
        except Exception as e:
            print(f"Error during prediction: {e}")
            # Use fallback behavior if prediction fails
            self._fallback_behavior(current_game_state)
        
        # Set buttons for the correct player
        if player == "1":
            self.my_command.player_buttons = self.buttn
        else:
            self.my_command.player2_buttons = self.buttn
            
        return self.my_command
    
    def _extract_features(self, game_state):
        # Extract the 21 input features used during training with exact column names
        p1 = game_state.player1
        p2 = game_state.player2
        
        # Calculate p1_rel_x (relative x position) and facing opponent
        p1_rel_x = p1.x_coord - p2.x_coord
        p1_facing_opponent = 1 if p1_rel_x < 0 else 0
        
        # Extracting the features in the exact order and names as in gameData.csv
        features = [
            game_state.timer,                     # timer
            p1.player_id,                        # p1_id (was causing error: using player_id instead of id)
            p1.health,                           # p1_health
            p1.x_coord,                          # p1_x
            p1.y_coord,                          # p1_y
            int(p1.is_jumping),                  # p1_jumping
            int(p1.is_crouching),                # p1_crouching
            int(p1.is_player_in_move),           # p1_in_move
            p1.move_id,                          # p1_move_id
            p2.player_id,                        # p2_id (was causing error: using player_id instead of id)
            p2.health,                           # p2_health
            p2.x_coord,                          # p2_x
            p2.y_coord,                          # p2_y
            int(p2.is_jumping),                  # p2_jumping
            int(p2.is_crouching),                # p2_crouching
            int(p2.is_player_in_move),           # p2_in_move
            p2.move_id,                          # p2_move_id
            p1_rel_x,                            # p1_rel_x
            p1.y_coord - p2.y_coord,             # p1_rel_y
            p1_facing_opponent,                  # p1_facing_opponent
            p1.health - p2.health                # p1_health_diff
        ]
        
        return features
        
    def _set_button_states(self, button_states):
        # Reset all buttons to False first
        self.buttn.up = False
        self.buttn.down = False
        self.buttn.left = False
        self.buttn.right = False
        self.buttn.A = False
        self.buttn.B = False
        self.buttn.X = False
        self.buttn.Y = False
        self.buttn.L = False
        self.buttn.R = False
        self.buttn.select = False
        self.buttn.start = False
        
        # Set button states based on model predictions
        # Order: [up, down, left, right, A, B, X, Y, L, R, select, start]
        button_mapping = [
            (0, 'up'), (1, 'down'), (2, 'left'), (3, 'right'),
            (4, 'A'), (5, 'B'), (6, 'X'), (7, 'Y'),
            (8, 'L'), (9, 'R'), (10, 'select'), (11, 'start')
        ]
        
        for idx, attr_name in button_mapping:
            if idx < len(button_states):
                setattr(self.buttn, attr_name, bool(button_states[idx]))
    
    def _fallback_behavior(self, game_state):
        """Basic fallback behavior if model prediction fails"""
        p1 = game_state.player1
        p2 = game_state.player2
        
        # Simple approach - move towards opponent if far, attack if close
        if abs(p1.x_coord - p2.x_coord) > 50:
            # Move towards opponent
            if p1.x_coord < p2.x_coord:
                self.buttn.right = True
            else:
                self.buttn.left = True
                
            # Random jump sometimes
            if np.random.random() < 0.1:
                self.buttn.up = True
        else:
            # Close enough to attack - use a random attack button
            attack_buttons = ['A', 'B', 'X', 'Y']
            selected_button = np.random.choice(attack_buttons)
            setattr(self.buttn, selected_button, True)
