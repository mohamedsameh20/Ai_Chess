import os
import warnings

# Hide pygame support prompt and suppress warnings BEFORE any pygame imports
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
warnings.filterwarnings('ignore', message=r'pkg_resources is deprecated as an API.*', category=UserWarning, module=r'pygame\.pkgdata')
warnings.filterwarnings('ignore', message=r'.*pkg_resources.*deprecated.*', category=UserWarning)

import sys
import pygame as p

from engine import GameState, Move
from chessAi import findRandomMoves, findBestMove
from multiprocessing import Process, Queue

# Safe sound playing function
def play_sound(sound):
    """Safely play a sound if it exists"""
    if sound is not None:
        try:
            sound.play()
        except:
            pass  # Ignore sound errors

p.mixer.init()
# Safely load sounds with error handling
try:
    move_sound = p.mixer.Sound("sounds/move-sound.mp3")
    capture_sound = p.mixer.Sound("sounds/capture.mp3")
    promote_sound = p.mixer.Sound("sounds/promote.mp3")
except:
    # Create dummy sound objects if files don't exist
    move_sound = None
    capture_sound = None
    promote_sound = None

# Game modes
HUMAN_VS_AI = 1
AI_VS_AI = 2
HUMAN_VS_HUMAN = 3

# AI Algorithm options
AI_ALGORITHMS = {
    "random": False,
    "alpha_beta": True,
    "iterative_deepening": False,
    "killer_heuristic": False,
    "mvv_lva": False
}

AI1_ALGORITHMS = {
    "random": False,
    "alpha_beta": True,
    "iterative_deepening": False,
    "killer_heuristic": False,
    "mvv_lva": False
}

AI2_ALGORITHMS = {
    "random": True,
    "alpha_beta": False,
    "iterative_deepening": False,
    "killer_heuristic": False,
    "mvv_lva": False
}

SCREEN_WIDTH = 1800
SCREEN_HEIGHT = 800

# Calculate optimal board size maintaining aspect ratio
# Reserve space for panels and maintain proportions
BOARD_SIZE = min(SCREEN_WIDTH * 0.6, SCREEN_HEIGHT * 0.9)  # 60% of width or 90% of height
BOARD_WIDTH = BOARD_HEIGHT = int(BOARD_SIZE)

# Panel dimensions - 2 horizontal tabs next to each other (removed search tree)
AVAILABLE_PANEL_WIDTH = SCREEN_WIDTH - BOARD_WIDTH
MOVE_LOG_PANEL_WIDTH = int(AVAILABLE_PANEL_WIDTH * 0.4)  # 40% - wider tab
AI_THINKING_PANEL_WIDTH = int(AVAILABLE_PANEL_WIDTH * 0.6)  # 60% - wider tab

# All panels have the same height as the board
PANEL_HEIGHT = BOARD_HEIGHT

# For compatibility with existing code
TOTAL_PANEL_WIDTH = MOVE_LOG_PANEL_WIDTH + AI_THINKING_PANEL_WIDTH

DIMENSION = 8
SQ_SIZE = BOARD_HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {}

ai_thinking_log = []
ai_thinking_scroll_offset = 0
ai_thinking_dragging = False
ai_thinking_last_mouse_y = 0

# Move log scrolling variables
move_log_scroll_offset = 0
move_log_dragging = False
move_log_last_mouse_y = 0

# Landing page dimensions - use windowed mode
LANDING_WIDTH = SCREEN_WIDTH
LANDING_HEIGHT = SCREEN_HEIGHT

# Button dimensions
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 60
BUTTON_MARGIN = 20

THEMES = {
    "classic": {
        "name": "Classic",
        "light": (240, 217, 181),
        "dark": (181, 136, 99),
        "highlight": (255, 255, 0),
        "possible": (255, 255, 51),
        "bg": (50, 50, 50)
    }
}

game_mode = None
current_screen = "landing"  # "landing" or "game"

def get_theme_colors():
    """Get current theme colors - always returns classic theme"""
    return THEMES["classic"]

def draw_button(screen, text, x, y, width, height, color, text_color, font):
    """Draw a modern button with gradient and shadow"""
    button_rect = p.Rect(x, y, width, height)
    
    # Create gradient effect
    for i in range(height):
        fade = i / height
        gradient_color = (
            int(color[0] + (255 - color[0]) * fade * 0.2),
            int(color[1] + (255 - color[1]) * fade * 0.2),
            int(color[2] + (255 - color[2]) * fade * 0.2)
        )
        p.draw.line(screen, gradient_color, (x, y + i), (x + width, y + i))
    
    p.draw.rect(screen, (255, 255, 255), button_rect, 2)
    
    shadow_surface = font.render(text, True, (0, 0, 0))
    text_surface = font.render(text, True, text_color)
    
    text_rect = text_surface.get_rect(center=button_rect.center)
    shadow_rect = shadow_surface.get_rect(center=(button_rect.centerx + 1, button_rect.centery + 1))
    
    screen.blit(shadow_surface, shadow_rect)
    screen.blit(text_surface, text_rect)
    
    return button_rect


def draw_ai_settings_screen(screen):
    """Draw AI algorithm selection screen"""
    global AI_ALGORITHMS, current_screen
    
    for y in range(LANDING_HEIGHT):
        color_intensity = int(30 + (y / LANDING_HEIGHT) * 50)
        color = (color_intensity, color_intensity + 20, color_intensity + 40)
        p.draw.line(screen, color, (0, y), (LANDING_WIDTH, y))
    
    # Title
    title_font = p.font.SysFont("Segoe UI", 42, True)
    title_text = title_font.render("AI Settings", True, (255, 255, 255))
    title_shadow = title_font.render("AI Settings", True, (100, 100, 100))
    title_rect = title_text.get_rect(center=(LANDING_WIDTH//2, 80))
    shadow_rect = title_shadow.get_rect(center=(LANDING_WIDTH//2 + 2, 82))
    
    screen.blit(title_shadow, shadow_rect)
    screen.blit(title_text, title_rect)
    
    # Subtitle
    subtitle_font = p.font.SysFont("Segoe UI", 18)
    subtitle_text = subtitle_font.render("Select AI algorithms to use (you can choose multiple)", True, (200, 220, 240))
    subtitle_rect = subtitle_text.get_rect(center=(LANDING_WIDTH//2, 120))
    screen.blit(subtitle_text, subtitle_rect)
    
    # Algorithm checkboxes
    checkbox_font = p.font.SysFont("Segoe UI", 16)
    checkbox_size = 20
    start_y = 170
    spacing = 50
    
    algorithms = [
        ("random", "Random Move Generator"),
        ("alpha_beta", "Alpha-Beta Pruning")
    ]
    
    checkbox_rects = []
    
    for i, (key, label) in enumerate(algorithms):
        y_pos = start_y + i * spacing
        checkbox_x = LANDING_WIDTH//2 - 150
        checkbox_rect = p.Rect(checkbox_x, y_pos, checkbox_size, checkbox_size)
        
        # Checkbox background
        is_checked = AI_ALGORITHMS.get(key, False)
        bg_color = (200, 240, 200) if is_checked else (240, 240, 240)
        p.draw.rect(screen, bg_color, checkbox_rect) 
        p.draw.rect(screen, (100, 100, 100), checkbox_rect, 2)
        
        # Check mark if selected
        if is_checked:
            p.draw.line(screen, (34, 139, 34), 
                       (checkbox_x + 4, y_pos + 10), 
                       (checkbox_x + 8, y_pos + 14), 3)
            p.draw.line(screen, (34, 139, 34), 
                       (checkbox_x + 8, y_pos + 14), 
                       (checkbox_x + 16, y_pos + 6), 3)
        
        # Label
        label_text = checkbox_font.render(label, True, (255, 255, 255))
        screen.blit(label_text, (checkbox_x + 30, y_pos))
        
        checkbox_rects.append((checkbox_rect, key))
    
    # Back and Start buttons
    button_font = p.font.SysFont("Segoe UI", 16, True)
    back_button = draw_button(screen, "← Back", 
                             50, LANDING_HEIGHT - 80, 
                             100, 40, 
                             (108, 117, 125), (255, 255, 255), button_font)
    
    start_button = draw_button(screen, "Start Game", 
                              LANDING_WIDTH - 150, LANDING_HEIGHT - 80, 
                              100, 40, 
                              (40, 167, 69), (255, 255, 255), button_font)
    
    # Handle events
    for event in p.event.get():
        if event.type == p.QUIT:
            return "quit"
        elif event.type == p.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            # Check checkbox clicks
            for checkbox_rect, key in checkbox_rects:
                if checkbox_rect.collidepoint(mouse_pos):
                    AI_ALGORITHMS[key] = not AI_ALGORITHMS.get(key, False)
            # Check button clicks
            if back_button.collidepoint(mouse_pos):
                current_screen = "landing"
                return "landing"
            elif start_button.collidepoint(mouse_pos):
                current_screen = "game"
                return "start_game"
    
    return "ai_settings"


def draw_ai_vs_ai_settings_screen(screen):
    """Draw AI vs AI algorithm selection screen with separate settings for each AI"""
    global AI1_ALGORITHMS, AI2_ALGORITHMS, current_screen
    
    for y in range(LANDING_HEIGHT):
        color_intensity = int(30 + (y / LANDING_HEIGHT) * 50)
        color = (color_intensity, color_intensity + 20, color_intensity + 40)
        p.draw.line(screen, color, (0, y), (LANDING_WIDTH, y))
    
    # Title
    title_font = p.font.SysFont("Segoe UI", 36, True)
    title_text = title_font.render("AI vs AI Settings", True, (255, 255, 255))
    title_shadow = title_font.render("AI vs AI Settings", True, (100, 100, 100))
    title_rect = title_text.get_rect(center=(LANDING_WIDTH//2, 60))
    shadow_rect = title_shadow.get_rect(center=(LANDING_WIDTH//2 + 2, 62))
    
    screen.blit(title_shadow, shadow_rect)
    screen.blit(title_text, title_rect)
    
    # Subtitle
    subtitle_font = p.font.SysFont("Segoe UI", 16)
    subtitle_text = subtitle_font.render("Configure algorithms for each AI player", True, (200, 220, 240))
    subtitle_rect = subtitle_text.get_rect(center=(LANDING_WIDTH//2, 90))
    screen.blit(subtitle_text, subtitle_rect)
    
    # Algorithm options
    algorithms = [
        ("random", "Random Move Generator"),
        ("alpha_beta", "Alpha-Beta Pruning")
    ]
    
    # AI 1 Section
    ai1_font = p.font.SysFont("Segoe UI", 20, True)
    ai1_text = ai1_font.render("AI Player 1 (White)", True, (255, 255, 255))
    screen.blit(ai1_text, (LANDING_WIDTH//4 - 100, 120))
    
    # AI 2 Section
    ai2_text = ai1_font.render("AI Player 2 (Black)", True, (255, 255, 255))
    screen.blit(ai2_text, (3 * LANDING_WIDTH//4 - 100, 120))
    
    # Draw checkboxes for both AIs
    checkbox_font = p.font.SysFont("Segoe UI", 14)
    checkbox_size = 18
    start_y = 150
    spacing = 40
    
    ai1_checkbox_rects = []
    ai2_checkbox_rects = []
    
    for i, (key, label) in enumerate(algorithms):
        y_pos = start_y + i * spacing
        
        # AI 1 checkboxes (left side)
        ai1_checkbox_x = LANDING_WIDTH//4 - 120
        ai1_checkbox_rect = p.Rect(ai1_checkbox_x, y_pos, checkbox_size, checkbox_size)
        
        is_ai1_checked = AI1_ALGORITHMS.get(key, False)
        ai1_bg_color = (200, 240, 200) if is_ai1_checked else (240, 240, 240)
        p.draw.rect(screen, ai1_bg_color, ai1_checkbox_rect)
        p.draw.rect(screen, (100, 100, 100), ai1_checkbox_rect, 2)
        
        # AI 1 check mark if selected
        if is_ai1_checked:
            p.draw.line(screen, (34, 139, 34), 
                       (ai1_checkbox_x + 3, y_pos + 9), 
                       (ai1_checkbox_x + 7, y_pos + 13), 2)
            p.draw.line(screen, (34, 139, 34), 
                       (ai1_checkbox_x + 7, y_pos + 13), 
                       (ai1_checkbox_x + 15, y_pos + 5), 2)
        
        # AI 1 label
        ai1_label_text = checkbox_font.render(label, True, (255, 255, 255))
        screen.blit(ai1_label_text, (ai1_checkbox_x + 25, y_pos + 2))
        
        ai1_checkbox_rects.append((ai1_checkbox_rect, key))
        
        # AI 2 checkboxes (right side)
        ai2_checkbox_x = 3 * LANDING_WIDTH//4 - 120
        ai2_checkbox_rect = p.Rect(ai2_checkbox_x, y_pos, checkbox_size, checkbox_size)
        
        is_ai2_checked = AI2_ALGORITHMS.get(key, False)
        ai2_bg_color = (240, 200, 200) if is_ai2_checked else (240, 240, 240)
        p.draw.rect(screen, ai2_bg_color, ai2_checkbox_rect)
        p.draw.rect(screen, (100, 100, 100), ai2_checkbox_rect, 2)
        
        # AI 2 check mark if selected
        if is_ai2_checked:
            p.draw.line(screen, (220, 20, 60), 
                       (ai2_checkbox_x + 3, y_pos + 9), 
                       (ai2_checkbox_x + 7, y_pos + 13), 2)
            p.draw.line(screen, (220, 20, 60), 
                       (ai2_checkbox_x + 7, y_pos + 13), 
                       (ai2_checkbox_x + 15, y_pos + 5), 2)
        
        # AI 2 label
        ai2_label_text = checkbox_font.render(label, True, (255, 255, 255))
        screen.blit(ai2_label_text, (ai2_checkbox_x + 25, y_pos + 2))
        
        ai2_checkbox_rects.append((ai2_checkbox_rect, key))
    
    # Back and Start buttons
    button_font = p.font.SysFont("Segoe UI", 16, True)
    back_button = draw_button(screen, "← Back", 
                             50, LANDING_HEIGHT - 80, 
                             100, 40, 
                             (108, 117, 125), (255, 255, 255), button_font)
    
    start_button = draw_button(screen, "Start Game", 
                              LANDING_WIDTH - 150, LANDING_HEIGHT - 80, 
                              100, 40, 
                              (40, 167, 69), (255, 255, 255), button_font)
    
    # Handle events
    for event in p.event.get():
        if event.type == p.QUIT:
            return "quit"
        elif event.type == p.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            # Check AI 1 checkbox clicks
            for checkbox_rect, key in ai1_checkbox_rects:
                if checkbox_rect.collidepoint(mouse_pos):
                    AI1_ALGORITHMS[key] = not AI1_ALGORITHMS.get(key, False)
            
            # Check AI 2 checkbox clicks
            for checkbox_rect, key in ai2_checkbox_rects:
                if checkbox_rect.collidepoint(mouse_pos):
                    AI2_ALGORITHMS[key] = not AI2_ALGORITHMS.get(key, False)
            
            # Check button clicks
            if back_button.collidepoint(mouse_pos):
                current_screen = "landing"
                return "landing"
            elif start_button.collidepoint(mouse_pos):
                current_screen = "game"
                return "start_game"
    
    return "ai_vs_ai_settings"


def draw_landing_page(screen):
    """Draw the landing page with game mode selection"""
    global game_mode, current_screen
    
    # Modern gradient background
    for y in range(LANDING_HEIGHT):
        color_intensity = int(30 + (y / LANDING_HEIGHT) * 50)
        color = (color_intensity, color_intensity + 20, color_intensity + 40)
        p.draw.line(screen, color, (0, y), (LANDING_WIDTH, y))
    subtitle_font = p.font.SysFont("Segoe UI", 25)
    button_font = p.font.SysFont("Segoe UI", 18, True)

    # Subtitle
    subtitle_text = subtitle_font.render("Choose Your Game Mode", True, (200, 220, 240))
    subtitle_rect = subtitle_text.get_rect(center=(LANDING_WIDTH//2, 150))
    screen.blit(subtitle_text, subtitle_rect)
    
    # Game mode buttons with modern colors
    button_y_start = 220
    button_spacing = BUTTON_HEIGHT + BUTTON_MARGIN
    
    # Human vs AI button (Blue theme)
    human_ai_button = draw_button(screen, "Human vs AI", 
                                 LANDING_WIDTH//2 - BUTTON_WIDTH//2, 
                                 button_y_start, 
                                 BUTTON_WIDTH, BUTTON_HEIGHT, 
                                 (70, 130, 180), (255, 255, 255), button_font)
    
    # AI vs AI button (Purple theme)
    ai_ai_button = draw_button(screen, "AI vs AI", 
                              LANDING_WIDTH//2 - BUTTON_WIDTH//2, 
                              button_y_start + button_spacing, 
                              BUTTON_WIDTH, BUTTON_HEIGHT, 
                              (138, 43, 226), (255, 255, 255), button_font)
    
    # Human vs Human button (Green theme)
    human_human_button = draw_button(screen, "Human vs Human", 
                                    LANDING_WIDTH//2 - BUTTON_WIDTH//2, 
                                    button_y_start + 2 * button_spacing, 
                                    BUTTON_WIDTH, BUTTON_HEIGHT, 
                                    (34, 139, 34), (255, 255, 255), button_font)
    
    # Handle events
    for event in p.event.get():
        if event.type == p.QUIT:
            return "quit"
        elif event.type == p.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            if human_ai_button.collidepoint(mouse_pos):
                game_mode = HUMAN_VS_AI
                current_screen = "ai_settings"
                return "ai_settings"
            elif ai_ai_button.collidepoint(mouse_pos):
                game_mode = AI_VS_AI
                current_screen = "ai_vs_ai_settings"
                return "ai_vs_ai_settings"
            elif human_human_button.collidepoint(mouse_pos):
                game_mode = HUMAN_VS_HUMAN
                current_screen = "game"
                return "start_game"
    
    return "continue"


def loadImages():
    pieces = ['bR', 'bN', 'bB', 'bQ', 'bK',
              'bp', 'wR', 'wN', 'wB', 'wQ', 'wK', 'wp']
    for piece in pieces:
        image_path = "images/" + piece + ".png"
        original_image = p.image.load(image_path)
        # p.transform.smoothscale is bit slower than p.transform.scale, using this to reduce pixelation and better visual quality for scaling images to larger sizes
        IMAGES[piece] = p.transform.smoothscale(
            original_image, (SQ_SIZE, SQ_SIZE))


def pawnPromotionPopup(screen, gs):
    """
    Display a promotion popup with piece images for user selection.
    Returns the selected promotion piece symbol ('Q', 'R', 'B', 'N').
    """
    # Safety check to prevent issues with game state
    if not hasattr(gs, 'whiteToMove'):
        return 'Q'  # Default fallback
        
    theme = get_theme_colors()
    
    # Determine the color of the promoting pawn based on whose turn it is
    # The pawn promoting belongs to the current player (whose turn it is)
    color = 'w' if gs.whiteToMove else 'b'
    
    # Overlay to darken the background - use screen dimensions
    overlay = p.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # Promotion box dimensions
    box_width = 400
    box_height = 180
    box_x = (SCREEN_WIDTH - box_width) // 2
    box_y = (SCREEN_HEIGHT - box_height) // 2
    
    # Draw main box with rounded corners effect
    box_rect = p.Rect(box_x, box_y, box_width, box_height)
    p.draw.rect(screen, (250, 250, 250), box_rect)
    p.draw.rect(screen, (100, 100, 100), box_rect, 3)
    
    # Title
    title_font = p.font.SysFont("Arial", 22, True)
    color_name = "White" if color == 'w' else "Black"
    title_text = title_font.render(f"Choose {color_name} Promotion Piece", True, (50, 50, 50))
    title_rect = title_text.get_rect(center=(box_x + box_width//2, box_y + 25))
    screen.blit(title_text, title_rect)
    
    # Piece options with their symbols and piece codes
    pieces = [
        ('Q', 'Queen'),
        ('R', 'Rook'), 
        ('B', 'Bishop'),
        ('N', 'Knight')
    ]
    
    # Calculate piece button layout
    piece_size = 60
    button_margin = 15
    total_width = 4 * piece_size + 3 * button_margin
    start_x = box_x + (box_width - total_width) // 2
    piece_y = box_y + 60
    
    # Create clickable rectangles for each piece
    piece_rects = []
    
    selected_piece = None
    clock = p.time.Clock()
    
    while selected_piece is None:
        for event in p.event.get():
            if event.type == p.QUIT:
                p.quit()
                sys.exit()
            elif event.type == p.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                
                # Check if any piece was clicked
                for i, (rect, symbol) in enumerate(piece_rects):
                    if rect.collidepoint(mouse_x, mouse_y):
                        selected_piece = symbol
                        break
        
        # Redraw the popup
        screen.blit(overlay, (0, 0))
        p.draw.rect(screen, (250, 250, 250), box_rect)
        p.draw.rect(screen, (100, 100, 100), box_rect, 3)
        screen.blit(title_text, title_rect)
        
        # Draw piece images and their clickable areas
        piece_rects.clear()
        mouse_pos = p.mouse.get_pos()
        
        for i, (symbol, name) in enumerate(pieces):
            piece_x = start_x + i * (piece_size + button_margin)
            piece_rect = p.Rect(piece_x, piece_y, piece_size, piece_size)
            piece_rects.append((piece_rect, symbol))
            
            # Highlight on hover
            if piece_rect.collidepoint(mouse_pos):
                p.draw.rect(screen, (255, 255, 100), piece_rect, 3)
            else:
                p.draw.rect(screen, (200, 200, 200), piece_rect, 2)
            
            # Draw the piece image with correct color
            piece_code = color + symbol
            if piece_code in IMAGES:
                # Scale the image to fit the button
                scaled_image = p.transform.smoothscale(IMAGES[piece_code], (piece_size - 4, piece_size - 4))
                image_rect = scaled_image.get_rect(center=piece_rect.center)
                screen.blit(scaled_image, image_rect)
            else:
                # Fallback: draw the piece symbol if image not found
                fallback_font = p.font.SysFont("Arial", 36, True)
                fallback_text = fallback_font.render(symbol, True, (0, 0, 0))
                text_rect = fallback_text.get_rect(center=piece_rect.center)
                screen.blit(fallback_text, text_rect)
            
            # Draw piece name below
            name_font = p.font.SysFont("Arial", 12)
            name_text = name_font.render(name, True, (80, 80, 80))
            name_rect = name_text.get_rect(center=(piece_x + piece_size//2, piece_y + piece_size + 15))
            screen.blit(name_text, name_rect)
        
        p.display.flip()
        clock.tick(60)  # Prevent excessive CPU usage
    
    return selected_piece

def main():
    global current_screen, game_mode
    p.init()
    
    # Start with windowed mode
    screen = p.display.set_mode((LANDING_WIDTH, LANDING_HEIGHT))
    p.display.set_caption("AI Project")
    clock = p.time.Clock()
    
    running = True
    
    while running:
        if current_screen == "landing":
            result = draw_landing_page(screen)
            if result == "quit":
                running = False
            elif result == "start_game":
                # Switch to windowed game screen
                screen = p.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                current_screen = "game"
                # Start the actual game
                game_result = run_chess_game(screen, clock)
                if game_result:  # Game ended, return to landing page
                    screen = p.display.set_mode((LANDING_WIDTH, LANDING_HEIGHT))
                    current_screen = "landing"
                else:  # Game was quit
                    running = False
            elif result == "ai_settings":
                current_screen = "ai_settings"
            elif result == "ai_vs_ai_settings":
                current_screen = "ai_vs_ai_settings"
        
        elif current_screen == "ai_settings":
            result = draw_ai_settings_screen(screen)
            if result == "quit":
                running = False
            elif result == "start_game":
                # Switch to windowed game screen
                screen = p.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                current_screen = "game"
                # Start the actual game
                game_result = run_chess_game(screen, clock)
                if game_result:  # Game ended, return to landing page
                    screen = p.display.set_mode((LANDING_WIDTH, LANDING_HEIGHT))
                    current_screen = "landing"
                else:  # Game was quit
                    running = False
            elif result == "landing":
                current_screen = "landing"
        
        elif current_screen == "ai_vs_ai_settings":
            result = draw_ai_vs_ai_settings_screen(screen)
            if result == "quit":
                running = False
            elif result == "start_game":
                # Switch to windowed game screen
                screen = p.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                current_screen = "game"
                # Start the actual game
                game_result = run_chess_game(screen, clock)
                if game_result:  # Game ended, return to landing page
                    screen = p.display.set_mode((LANDING_WIDTH, LANDING_HEIGHT))
                    current_screen = "landing"
                else:  # Game was quit
                    running = False
            elif result == "landing":
                current_screen = "landing"
            
        p.display.flip()
        clock.tick(MAX_FPS)
    
    p.quit()
    sys.exit()

def run_chess_game(screen, clock):
    global current_screen, game_mode
    
    theme = get_theme_colors()
    screen.fill(p.Color(theme["bg"]))
    moveLogFont = p.font.SysFont("Times New Roman", 14, False, False)
    
    # Creating gamestate object calling our constructor
    gs = GameState()
    
    # Get board array for GUI compatibility
    board_array = gs.get_board_array()
    
    # Set up players based on game mode
    if game_mode == HUMAN_VS_AI:
        playerWhiteHuman = True
        playerBlackHuman = False
    elif game_mode == AI_VS_AI:
        playerWhiteHuman = False
        playerBlackHuman = False
    else:  # HUMAN_VS_HUMAN
        playerWhiteHuman = True
        playerBlackHuman = True
    
    # if a user makes a move we can ckeck if its in the list of valid moves
    validMoves = gs.getValidMoves()
    moveMade = False  # if user makes a valid moves and the gamestate changes then we should generate new set of valid move
    animate = False  # flag var for when we should animate a move
    loadImages()
    squareSelected = ()  # keep tracks of last click
    # clicking to own piece and location where to move[(6,6),(4,4)]
    playerClicks = []
    gameOver = False  # gameover if checkmate or stalemate
    AIThinking = False  # True if ai is thinking
    moveFinderProcess = None
    moveUndone = False
    pieceCaptured = False
    positionHistory = ""
    previousPos = ""
    countMovesForDraw = 0
    COUNT_DRAW = 0
    promotion_in_progress = False  # Flag to prevent double promotion popups
    
    while True:
        humanTurn = (gs.whiteToMove and playerWhiteHuman) or (
            not gs.whiteToMove and playerBlackHuman)
        for e in p.event.get():
            if e.type == p.QUIT:
                return False
            # Mouse Handler
            elif e.type == p.MOUSEBUTTONDOWN:
                if not gameOver:  # allow mouse handling only if its not game over
                    location = p.mouse.get_pos()
                    col = location[0]//SQ_SIZE
                    row = location[1]//SQ_SIZE
                    
                    # Only process clicks on the chess board
                    if col < 8:  # Valid board click
                        # if user clicked on same square twice or user click outside board
                        if squareSelected == (row, col):
                            squareSelected = ()  # deselect
                            playerClicks = []  # clear player clicks
                        else:
                            squareSelected = (row, col)
                            # append player both clicks (place and destination)
                            playerClicks.append(squareSelected)
                        # after second click (at destination)
                        if len(playerClicks) == 2 and humanTurn:
                            # user generated a move
                            board_array = gs.get_board_array()
                            move = Move(playerClicks[0], playerClicks[1], board_array)
                            for i in range(len(validMoves)):
                                # check if the move is in the validMoves
                                if move == validMoves[i]:
                                    # Check if a piece is captured at the destination square
                                    if board_array[validMoves[i].endRow][validMoves[i].endCol] != '--':
                                        pieceCaptured = True
                                    
                                    # Create a copy of the move to work with
                                    chosen_move = validMoves[i]
                                    
                                    # Handle pawn promotion ONLY for human players
                                    if chosen_move.isPawnPromotion and humanTurn and not promotion_in_progress:
                                        promotion_in_progress = True
                                        # Show pawn promotion popup and get the selected piece
                                        promotion_choice = pawnPromotionPopup(screen, gs)
                                        # Apply the promotion choice to the move
                                        chosen_move.promotion = promotion_choice
                                        promotion_in_progress = False
                                    elif chosen_move.isPawnPromotion and not hasattr(chosen_move, 'promotion'):
                                        # If it's an AI move or promotion wasn't set, default to Queen
                                        chosen_move.promotion = 'Q'
                                    
                                    gs.makeMove(chosen_move)
                                    
                                    if chosen_move.isPawnPromotion:
                                        play_sound(promote_sound)
                                        pieceCaptured = False
                                    # add sound for human move
                                    if (pieceCaptured or move.isEnpassantMove):
                                        # Play capture sound
                                        play_sound(capture_sound)
                                    elif not move.isPawnPromotion:
                                        # Play move sound
                                        play_sound(move_sound)
                                    pieceCaptured = False
                                    moveMade = True
                                    animate = True
                                    squareSelected = ()
                                    playerClicks = []
                                    break  # Important: break out of the loop once move is found
                            if not moveMade:
                                playerClicks = [squareSelected]

            # Key Handler
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:  # undo when z is pressed
                    gs.undoMove()
                    moveMade = True
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True
                elif e.key == p.K_r:  # reset board when 'r' is pressed
                    gs = GameState()
                    validMoves = gs.getValidMoves()
                    squareSelected = ()
                    playerClicks = []
                    moveMade = False
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True
                elif e.key == p.K_ESCAPE:  # Return to landing page
                    current_screen = "landing"
                    return True
            
            # Mouse wheel scroll handling for panels - horizontal layout
            elif e.type == p.MOUSEWHEEL or e.type == p.MOUSEBUTTONDOWN or e.type == p.MOUSEBUTTONUP or e.type == p.MOUSEMOTION:
                mouse_pos = p.mouse.get_pos()
                # Update panel detection for horizontal layout
                in_move_log_panel = (mouse_pos[0] >= BOARD_WIDTH and mouse_pos[0] < BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH)
                in_ai_panel = (mouse_pos[0] >= BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH and mouse_pos[0] < BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + AI_THINKING_PANEL_WIDTH)
                
                global ai_thinking_scroll_offset, ai_thinking_dragging, ai_thinking_last_mouse_y
                global move_log_scroll_offset, move_log_dragging, move_log_last_mouse_y

                # Mouse wheel
                if e.type == p.MOUSEWHEEL:
                    scroll_speed = 40
                    if in_ai_panel:
                        # e.y is positive when scrolling up
                        ai_thinking_scroll_offset = max(0, ai_thinking_scroll_offset - e.y * scroll_speed)
                    elif in_move_log_panel:
                        move_log_scroll_offset = max(0, move_log_scroll_offset - e.y * scroll_speed)

                # Left mouse button pressed -> start dragging
                elif e.type == p.MOUSEBUTTONDOWN and e.button == 1:
                    if in_ai_panel:
                        ai_thinking_dragging = True
                        ai_thinking_last_mouse_y = mouse_pos[1]
                    elif in_move_log_panel:
                        move_log_dragging = True
                        move_log_last_mouse_y = mouse_pos[1]

                # Left mouse button released -> stop dragging
                elif e.type == p.MOUSEBUTTONUP and e.button == 1:
                    ai_thinking_dragging = False
                    move_log_dragging = False

                # Mouse moved -> handle dragging
                elif e.type == p.MOUSEMOTION:
                    if ai_thinking_dragging:
                        dy = mouse_pos[1] - ai_thinking_last_mouse_y
                        ai_thinking_last_mouse_y = mouse_pos[1]
                        ai_thinking_scroll_offset = max(0, ai_thinking_scroll_offset - dy)
                    elif move_log_dragging:
                        dy = mouse_pos[1] - move_log_last_mouse_y
                        move_log_last_mouse_y = mouse_pos[1]
                        move_log_scroll_offset = max(0, move_log_scroll_offset - dy)

        # AI move finder
        if not gameOver and not humanTurn and not moveUndone:
            if not AIThinking:
                AIThinking = True
                returnQueue = Queue()
                thinkingQueue = Queue()  # New queue for thinking process
                
                # Determine which AI algorithms to use and prepare AI info
                if game_mode == AI_VS_AI:
                    # In AI vs AI mode, use different algorithms for each player
                    if gs.whiteToMove:
                        current_ai_algorithms = AI1_ALGORITHMS  # White player
                        ai_color = "White"
                        # Determine AI mode based on enabled algorithms
                        if AI1_ALGORITHMS.get("alpha_beta", False):
                            ai_mode = "Alpha-Beta"
                        elif AI1_ALGORITHMS.get("random", False):
                            ai_mode = "Random"
                        else:
                            ai_mode = "Random"  # Fallback
                    else:
                        current_ai_algorithms = AI2_ALGORITHMS  # Black player
                        ai_color = "Black"
                        if AI2_ALGORITHMS.get("alpha_beta", False):
                            ai_mode = "Alpha-Beta"
                        elif AI2_ALGORITHMS.get("random", False):
                            ai_mode = "Random"
                        else:
                            ai_mode = "Random"  # Fallback
                else:
                    # In Human vs AI mode, use the single AI settings
                    current_ai_algorithms = AI_ALGORITHMS
                    if gs.whiteToMove:
                        ai_color = "White"
                        if AI_ALGORITHMS.get("alpha_beta", False):
                            ai_mode = "Alpha-Beta"
                        elif AI_ALGORITHMS.get("random", False):
                            ai_mode = "Random"
                        else:
                            ai_mode = "Random"  # Fallback
                    else:
                        ai_color = "Black"
                        if AI_ALGORITHMS.get("alpha_beta", False):
                            ai_mode = "Alpha-Beta"
                        elif AI_ALGORITHMS.get("random", False):
                            ai_mode = "Random"
                        else:
                            ai_mode = "Random"  # Fallback
                
                # Create AI info dictionary
                ai_info = {
                    'color': ai_color,
                    'mode': ai_mode
                }
                
                moveFinderProcess = Process(target=findBestMove, args=(
                    gs, validMoves, returnQueue, current_ai_algorithms, thinkingQueue, ai_info))
                moveFinderProcess.start()
            if not moveFinderProcess.is_alive():
                # Collect thinking messages from queue
                while not thinkingQueue.empty():
                    try:
                        thinking_msg = thinkingQueue.get_nowait()
                        ai_thinking_log.append(thinking_msg)
                    except:
                        break
                
                AIMove = returnQueue.get()
                if AIMove is None:
                    # Create AI info for fallback call
                    if game_mode == AI_VS_AI:
                        ai_color = "White" if gs.whiteToMove else "Black"
                        ai_mode = "Random-Fallback"
                    else:
                        ai_color = "White" if gs.whiteToMove else "Black"
                        ai_mode = "Random-Fallback"
                    
                    ai_info = {'color': ai_color, 'mode': ai_mode}
                    AIMove = findRandomMoves(validMoves, thinkingQueue, ai_info)

                board_array = gs.get_board_array()
                if board_array[AIMove.endRow][AIMove.endCol] != '--':
                    pieceCaptured = True

                gs.makeMove(AIMove)

                if AIMove.isPawnPromotion:
                    # AI promotion - don't show popup, the promotion piece is already chosen by AI
                    # The Move.promotion attribute should already be set by the AI
                    play_sound(promote_sound)
                    pieceCaptured = False

                if (pieceCaptured or AIMove.isEnpassantMove):
                    play_sound(capture_sound)
                elif not AIMove.isPawnPromotion:
                    play_sound(move_sound)
                pieceCaptured = False
                AIThinking = False
                moveMade = True
                animate = True
                squareSelected = ()
                playerClicks = []

        if moveMade:
            if countMovesForDraw == 0 or countMovesForDraw == 1 or countMovesForDraw == 2 or countMovesForDraw == 3:
                countMovesForDraw += 1
            if countMovesForDraw == 4:
                positionHistory += gs.getBoardString()
                if previousPos == positionHistory:
                    COUNT_DRAW += 1
                    positionHistory = ""
                    countMovesForDraw = 0
                else:
                    previousPos = positionHistory
                    positionHistory = ""
                    countMovesForDraw = 0
                    COUNT_DRAW = 0
            # Call animateMove to animate the move
            if animate:
                animateMove(gs.moveLog[-1], screen, gs.get_board_array(), clock)
            # generate new set of valid move if valid move is made
            validMoves = gs.getValidMoves()
            moveMade = False
            animate = False
            moveUndone = False

        drawGameState(screen, gs, validMoves, squareSelected, moveLogFont)

        if COUNT_DRAW == 1:
            gameOver = True
            text = 'Draw due to repetition'
            drawEndGameText(screen, text)
            # Handle return to menu
            for event in p.event.get():
                if event.type == p.KEYDOWN or event.type == p.MOUSEBUTTONDOWN:
                    return True  # Return to main menu
        if gs.stalemate:
            gameOver = True
            text = 'Stalemate'
            drawEndGameText(screen, text)
            # Handle return to menu
            for event in p.event.get():
                if event.type == p.KEYDOWN or event.type == p.MOUSEBUTTONDOWN:
                    return True  # Return to main menu
        elif gs.checkmate:
            gameOver = True
            text = 'Black wins by checkmate' if gs.whiteToMove else 'White wins by checkmate'
            drawEndGameText(screen, text)
            # Handle return to menu
            for event in p.event.get():
                if event.type == p.KEYDOWN or event.type == p.MOUSEBUTTONDOWN:
                    return True  # Return to main menu

        clock.tick(MAX_FPS)
        p.display.flip()


def drawGameState(screen, gs, validMoves, squareSelected, moveLogFont):
    drawSquare(screen)  # draw square on board
    highlightSquares(screen, gs, validMoves, squareSelected)
    drawPieces(screen, gs.get_board_array())
    drawDualPanels(screen, gs, moveLogFont)


def drawSquare(screen):
    global colors
    theme = get_theme_colors()
    colors = [p.Color(theme["light"]), p.Color(theme["dark"])]
    
    # Draw the squares
    for row in range(DIMENSION):
        for col in range(DIMENSION):
            color = colors[((row + col) % 2)]
            p.draw.rect(screen, color, p.Rect(
                col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE))
    
    # Add coordinate labels (a-h, 1-8)
    font = p.font.SysFont("Calibri", 16, True)
    label_color = p.Color("black")
    
    # Files (a-h) at the bottom
    files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    for col in range(DIMENSION):
        text = font.render(files[col], True, label_color)
        # Position at bottom right of each column
        x = col * SQ_SIZE + SQ_SIZE - 12
        y = (DIMENSION - 1) * SQ_SIZE + SQ_SIZE - 20
        screen.blit(text, (x, y))
    
    # Ranks (1-8) at the left side
    ranks = ['8', '7', '6', '5', '4', '3', '2', '1']
    for row in range(DIMENSION):
        text = font.render(ranks[row], True, label_color)
        # Position at top left of each row
        x = 5
        y = row * SQ_SIZE + 5
        screen.blit(text, (x, y))


def highlightSquares(screen, gs, validMoves, squareSelected):
    theme = get_theme_colors()
    if squareSelected != ():  # make sure there is a square to select
        row, col = squareSelected
        board_array = gs.get_board_array()
        # make sure they click there own piece
        if board_array[row][col][0] == ('w' if gs.whiteToMove else 'b'):
            # highlight selected piece square
            # Surface in pygame used to add images or transperency feature
            s = p.Surface((SQ_SIZE, SQ_SIZE))
            # set_alpha --> transperancy value (0 transparent)
            s.set_alpha(100)
            s.fill(p.Color(theme["highlight"]))
            screen.blit(s, (col*SQ_SIZE, row*SQ_SIZE))
            # highlighting valid square
            s.fill(p.Color(theme["possible"]))
            for move in validMoves:
                if move.startRow == row and move.startCol == col:
                    screen.blit(s, (move.endCol*SQ_SIZE, move.endRow*SQ_SIZE))


def drawPieces(screen, board):
    for row in range(DIMENSION):
        for col in range(DIMENSION):
            piece = board[row][col]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(
                    col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE))


def drawDualPanels(screen, gs, font):
    """Draw 2 horizontal panels: Move History | AI Thinking"""
    global ai_thinking_log
    theme = get_theme_colors()
    
    # Panel positions - 2 horizontal panels next to the board
    # Move History Panel (left)
    moveHistoryRect = p.Rect(BOARD_WIDTH, 0, MOVE_LOG_PANEL_WIDTH, PANEL_HEIGHT)
    p.draw.rect(screen, p.Color(theme["bg"]), moveHistoryRect)
    p.draw.rect(screen, p.Color("white"), moveHistoryRect, 2)
    
    # AI Thinking Panel (right)
    aiThinkingRect = p.Rect(BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH, 0, AI_THINKING_PANEL_WIDTH, PANEL_HEIGHT)
    p.draw.rect(screen, p.Color(theme["bg"]), aiThinkingRect)
    p.draw.rect(screen, p.Color("white"), aiThinkingRect, 2)
    
    # Draw panel titles at the top of each panel
    title_font = p.font.SysFont("Arial", 14, True)
    title_y = 8
    
    # Move History title
    move_title = title_font.render("Move History", True, p.Color('white'))
    move_title_rect = move_title.get_rect(center=(moveHistoryRect.centerx, title_y + move_title.get_height()//2))
    screen.blit(move_title, move_title_rect)
    
    # AI Thinking title
    ai_title = title_font.render("AI Thinking", True, p.Color('white'))
    ai_title_rect = ai_title.get_rect(center=(aiThinkingRect.centerx, title_y + ai_title.get_height()//2))
    screen.blit(ai_title, ai_title_rect)
    
    # Draw panel content with adjusted rectangles to account for titles
    title_height = 25
    moveHistoryContentRect = p.Rect(moveHistoryRect.left, moveHistoryRect.top + title_height, 
                                   moveHistoryRect.width, moveHistoryRect.height - title_height)
    aiThinkingContentRect = p.Rect(aiThinkingRect.left, aiThinkingRect.top + title_height,
                                  aiThinkingRect.width, aiThinkingRect.height - title_height)
    
    drawMoveLog(screen, gs, font, moveHistoryContentRect)
    drawAIThinking(screen, font, aiThinkingContentRect)





def drawTabbedPanel(screen, gs, font):
    """Draw the tabbed panel with Move History and AI Thinking tabs"""
    global current_tab, ai_thinking_log
    theme = get_theme_colors()
    
    # Main panel rectangle
    panelRect = p.Rect(BOARD_WIDTH, 0, MOVE_LOG_PANEL_WIDTH, PANEL_HEIGHT)
    p.draw.rect(screen, p.Color(theme["bg"]), panelRect)
    p.draw.rect(screen, p.Color("white"), panelRect, 2)
    
    # Tab dimensions
    tab_height = 40
    tab_width = MOVE_LOG_PANEL_WIDTH // 2
    
    # Draw tabs
    moves_tab_rect = p.Rect(BOARD_WIDTH, 0, tab_width, tab_height)
    ai_tab_rect = p.Rect(BOARD_WIDTH + tab_width, 0, tab_width, tab_height)
    
    # Tab colors
    moves_color = (70, 130, 180) if current_tab == "moves" else (100, 100, 100)
    ai_color = (138, 43, 226) if current_tab == "ai_thinking" else (100, 100, 100)
    
    # Draw tab backgrounds
    p.draw.rect(screen, moves_color, moves_tab_rect)
    p.draw.rect(screen, ai_color, ai_tab_rect)
    p.draw.rect(screen, p.Color("white"), moves_tab_rect, 2)
    p.draw.rect(screen, p.Color("white"), ai_tab_rect, 2)
    
    # Tab text
    tab_font = p.font.SysFont("Arial", 12, True)
    moves_text = tab_font.render("Move History", True, p.Color('white'))
    ai_text = tab_font.render("AI Thinking", True, p.Color('white'))
    
    moves_text_rect = moves_text.get_rect(center=moves_tab_rect.center)
    ai_text_rect = ai_text.get_rect(center=ai_tab_rect.center)
    
    screen.blit(moves_text, moves_text_rect)
    screen.blit(ai_text, ai_text_rect)
    
    # Content area
    content_rect = p.Rect(BOARD_WIDTH, tab_height, MOVE_LOG_PANEL_WIDTH, PANEL_HEIGHT - tab_height)
    
    if current_tab == "moves":
        drawMoveLog(screen, gs, font, content_rect)
    else:
        drawAIThinking(screen, font, content_rect)


def drawMoveLog(screen, gs, font, content_rect):
    """Draw the move history in a two-column table format with improved scrolling"""
    global move_log_scroll_offset
    theme = get_theme_colors()
    
    moveLog = gs.moveLog
    padding = 8  # Reduced padding for narrow panel
    lineSpacing = 6
    textY = content_rect.top + padding

    if not moveLog:
        no_moves_text = font.render("No moves yet", True, p.Color('gray'))
        no_moves_rect = no_moves_text.get_rect(center=(content_rect.centerx, content_rect.centery))
        screen.blit(no_moves_text, no_moves_rect)
        return

    # Create a scrollable content area
    content_start_y = textY
    available_height = content_rect.bottom - content_start_y - 10
    
    # Calculate layout for two-column table
    move_number_width = 30
    white_move_width = (content_rect.width - 2 * padding - move_number_width - 10) // 2
    black_move_width = white_move_width
    
    # Pre-process moves to calculate total content height
    processed_moves = []
    virtual_y = 0
    
    # Header row
    header_font = p.font.SysFont("Arial", 12, True)
    header_height = header_font.get_height() + 6
    processed_moves.append(('header', None, None, None, virtual_y))
    virtual_y += header_height + lineSpacing
    
    for i in range(0, len(moveLog), 2):
        move_number = i//2 + 1
        white_move = str(moveLog[i]) if i < len(moveLog) else ""
        black_move = str(moveLog[i+1]) if i+1 < len(moveLog) else ""
        
        # Check if this is the most recent move
        is_recent_white = i == len(moveLog) - 1
        is_recent_black = i+1 == len(moveLog) - 1
        
        processed_moves.append(('move', move_number, white_move, black_move, virtual_y, is_recent_white, is_recent_black))
        virtual_y += font.get_height() + lineSpacing
    
    # Calculate total content height and adjust scroll bounds
    total_content_height = virtual_y
    max_scroll = max(0, total_content_height - available_height)
    move_log_scroll_offset = min(move_log_scroll_offset, max_scroll)
    
    # Auto-scroll to bottom when new content is added
    if len(processed_moves) > 1:  # More than just header
        was_at_bottom = move_log_scroll_offset >= max_scroll - 10
        if was_at_bottom:
            move_log_scroll_offset = max_scroll
    
    # Create clipping rect for scrollable content
    clip_rect = p.Rect(content_rect.left, content_start_y, content_rect.width, available_height)
    original_clip = screen.get_clip()
    screen.set_clip(clip_rect)
    
    # Draw the visible moves with scroll offset
    for move_data in processed_moves:
        if move_data[0] == 'header':
            _, _, _, _, line_y = move_data
            adjusted_y = content_start_y + line_y - move_log_scroll_offset
            
            if adjusted_y + header_height >= content_start_y and adjusted_y <= content_start_y + available_height:
                # Draw table headers
                header_y = adjusted_y + 3
                header_font = p.font.SysFont("Arial", 12, True)
                
                # Column headers
                num_text = header_font.render("#", True, p.Color('lightgray'))
                white_text = header_font.render("White", True, p.Color('lightgray'))
                black_text = header_font.render("Black", True, p.Color('lightgray'))
                
                screen.blit(num_text, (content_rect.left + padding, header_y))
                screen.blit(white_text, (content_rect.left + padding + move_number_width, header_y))
                screen.blit(black_text, (content_rect.left + padding + move_number_width + white_move_width + 5, header_y))
                
                # Draw separator line
                separator_y = adjusted_y + header_height - 2
                p.draw.line(screen, p.Color('gray'), 
                           (content_rect.left + padding, separator_y), 
                           (content_rect.right - padding, separator_y), 1)
        
        elif move_data[0] == 'move':
            _, move_number, white_move, black_move, line_y, is_recent_white, is_recent_black = move_data
            adjusted_y = content_start_y + line_y - move_log_scroll_offset
            
            if adjusted_y + font.get_height() >= content_start_y and adjusted_y <= content_start_y + available_height:
                # Background highlight for alternating rows
                row_color = (40, 40, 50) if move_number % 2 == 0 else (30, 30, 40)
                row_rect = p.Rect(content_rect.left + padding, adjusted_y - 2, 
                                content_rect.width - 2 * padding, font.get_height() + 4)
                p.draw.rect(screen, row_color, row_rect)
                
                # Draw move number
                num_text = font.render(f"{move_number}.", True, p.Color('lightblue'))
                screen.blit(num_text, (content_rect.left + padding, adjusted_y))
                
                # Draw white move with highlight if recent
                if white_move:
                    if is_recent_white:
                        # Recent move glow effect
                        glow_rect = p.Rect(content_rect.left + padding + move_number_width - 2, adjusted_y - 2,
                                         white_move_width + 4, font.get_height() + 4)
                        glow_surface = p.Surface((glow_rect.width, glow_rect.height))
                        glow_surface.set_alpha(100)
                        glow_surface.fill(p.Color('gold'))
                        screen.blit(glow_surface, glow_rect)
                        white_text_color = p.Color('black')
                    else:
                        white_text_color = p.Color('white')
                    
                    white_text = font.render(white_move, True, white_text_color)
                    screen.blit(white_text, (content_rect.left + padding + move_number_width, adjusted_y))
                
                # Draw black move with highlight if recent
                if black_move:
                    if is_recent_black:
                        # Recent move glow effect
                        glow_rect = p.Rect(content_rect.left + padding + move_number_width + white_move_width + 3, adjusted_y - 2,
                                         black_move_width + 4, font.get_height() + 4)
                        glow_surface = p.Surface((glow_rect.width, glow_rect.height))
                        glow_surface.set_alpha(100)
                        glow_surface.fill(p.Color('gold'))
                        screen.blit(glow_surface, glow_rect)
                        black_text_color = p.Color('black')
                    else:
                        black_text_color = p.Color('white')
                    
                    black_text = font.render(black_move, True, black_text_color)
                    screen.blit(black_text, (content_rect.left + padding + move_number_width + white_move_width + 5, adjusted_y))
    
    # Restore original clipping
    screen.set_clip(original_clip)
    
    # Draw custom scroll indicator if content is scrollable
    if max_scroll > 0:
        indicator_height = max(20, int(available_height * (available_height / total_content_height)))
        indicator_width = 8
        indicator_x = content_rect.right - indicator_width - 3
        
        # Background for scroll indicator
        indicator_bg_rect = p.Rect(indicator_x, content_start_y, indicator_width, available_height)
        p.draw.rect(screen, (50, 50, 60), indicator_bg_rect)
        p.draw.rect(screen, (100, 100, 120), indicator_bg_rect, 1)
        
        # Calculate indicator position
        scroll_ratio = move_log_scroll_offset / max_scroll
        indicator_pos = int(scroll_ratio * (available_height - indicator_height))
        indicator_rect = p.Rect(indicator_x, content_start_y + indicator_pos, indicator_width, indicator_height)
        p.draw.rect(screen, (180, 180, 200), indicator_rect)
        p.draw.rect(screen, (220, 220, 240), indicator_rect, 1)


def drawAIThinking(screen, font, content_rect):
    """Draw the AI thinking process in the content area with scrolling support"""
    global ai_thinking_log, ai_thinking_scroll_offset
    
    padding = 8  # Reduced padding
    lineSpacing = 4
    textY = content_rect.top + padding
    
    # Create a scrollable content area
    content_start_y = textY
    available_height = content_rect.bottom - content_start_y - 10
    
    # Optimized for 450px width - calculate precise character limit
    char_width = font.size("M")[0]
    available_text_width = content_rect.width - (2 * padding) - 10  # Extra margin for scroll indicator
    max_chars_per_line = max(35, available_text_width // char_width)
    
    # Pre-process all entries to calculate total content height
    processed_lines = []
    virtual_y = 0
    
    for entry in ai_thinking_log:
        # Normalize whitespace and remove newlines to avoid unnecessary blank lines
        entry_clean = ' '.join(entry.split())
        if len(entry_clean) > max_chars_per_line:
            # Intelligent text wrapping - try to break at sensible points
            words = entry_clean.split()
            current_line = ""
            
            for word in words:
                # Check if adding this word would exceed the line limit
                test_line = current_line + word + " "
                if len(test_line) > max_chars_per_line:
                    if current_line:
                        processed_lines.append((current_line.strip(), virtual_y))
                        virtual_y += font.get_height() + lineSpacing
                    current_line = word + " "
                else:
                    current_line = test_line
            
            # Add the remaining text
            if current_line.strip():
                processed_lines.append((current_line.strip(), virtual_y))
                virtual_y += font.get_height() + lineSpacing
        else:
            processed_lines.append((entry_clean, virtual_y))
            virtual_y += font.get_height() + lineSpacing
    
    # Calculate total content height and adjust scroll bounds
    total_content_height = virtual_y
    max_scroll = max(0, total_content_height - available_height)
    ai_thinking_scroll_offset = min(ai_thinking_scroll_offset, max_scroll)
    
    # Auto-scroll to bottom when new content is added
    if len(processed_lines) > 0:
        # Check if we were already at or near the bottom
        was_at_bottom = ai_thinking_scroll_offset >= max_scroll - 10
        if was_at_bottom:
            ai_thinking_scroll_offset = max_scroll
    
    # Create clipping rect for scrollable content
    clip_rect = p.Rect(content_rect.left, content_start_y, content_rect.width, available_height)
    original_clip = screen.get_clip()
    screen.set_clip(clip_rect)
    
    # Draw the visible lines with scroll offset
    for line_text, line_y in processed_lines:
        adjusted_y = content_start_y + line_y - ai_thinking_scroll_offset
        
        # Only render lines that are visible
        if adjusted_y + font.get_height() >= content_start_y and adjusted_y <= content_start_y + available_height:
            textObject = font.render(line_text, True, p.Color('white'))
            screen.blit(textObject, (content_rect.left + padding, adjusted_y))
    
    # Restore original clipping
    screen.set_clip(original_clip)
    
    # Draw scroll indicator if content is scrollable
    if max_scroll > 0:
        indicator_height = max(20, int(available_height * (available_height / total_content_height)))
        indicator_width = 6
        indicator_x = content_rect.right - indicator_width - 3
        
        # Background for scroll indicator
        indicator_bg_rect = p.Rect(indicator_x, content_start_y, indicator_width, available_height)
        p.draw.rect(screen, (40, 40, 40), indicator_bg_rect)
        p.draw.rect(screen, (80, 80, 80), indicator_bg_rect, 1)
        
        # Calculate indicator position
        scroll_ratio = ai_thinking_scroll_offset / max_scroll
        indicator_pos = int(scroll_ratio * (available_height - indicator_height))
        indicator_rect = p.Rect(indicator_x, content_start_y + indicator_pos, indicator_width, indicator_height)
        p.draw.rect(screen, (180, 180, 180), indicator_rect)
        p.draw.rect(screen, (220, 220, 220), indicator_rect, 1)


# animating a move
def animateMove(move, screen, board, clock):
    global colors
    # change in row, col
    deltaRow = move.endRow - move.startRow
    deltaCol = move.endCol - move.startCol
    framesPerSquare = 5  # frames move one square
    # how many frame the animation will take
    frameCount = (abs(deltaRow) + abs(deltaCol)) * framesPerSquare
    # generate all the coordinates
    for frame in range(frameCount + 1):
        # how much does the row and col move by
        row, col = ((move.startRow + deltaRow*frame/frameCount, move.startCol +
                    deltaCol*frame/frameCount))  # how far through the animation
        # for each frame draw the moved piece
        drawSquare(screen)
        drawPieces(screen, board)

        # erase the piece moved from its ending squares
        color = colors[(move.endRow + move.endCol) %
                       2]  # get color of the square
        endSquare = p.Rect(move.endCol*SQ_SIZE, move.endRow *
                           SQ_SIZE, SQ_SIZE, SQ_SIZE)  # pygame rectangle
        p.draw.rect(screen, color, endSquare)

        # draw the captured piece back
        if move.pieceCaptured != '--':
            if move.isEnpassantMove:
                enPassantRow = move.endRow + \
                    1 if move.pieceCaptured[0] == 'b' else move.endRow - 1
                endSquare = p.Rect(move.endCol*SQ_SIZE, enPassantRow *
                                   SQ_SIZE, SQ_SIZE, SQ_SIZE)  # pygame rectangle
            screen.blit(IMAGES[move.pieceCaptured], endSquare)

        # draw moving piece
        screen.blit(IMAGES[move.pieceMoved], p.Rect(
            col*SQ_SIZE, row*SQ_SIZE, SQ_SIZE, SQ_SIZE))

        p.display.flip()
        clock.tick(240)


def drawEndGameText(screen, text):
    # Overlay to darken the background - use screen dimensions
    overlay = p.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # Game over box
    box_width = 400
    box_height = 200
    box_x = (SCREEN_WIDTH - box_width) // 2
    box_y = (SCREEN_HEIGHT - box_height) // 2
    
    # Determine the color based on result
    if "wins" in text.lower():
        if "white" in text.lower():
            color = (34, 139, 34)  # Forest Green
        else:
            color = (220, 20, 60)  # Crimson
    else:  # Draw
        color = (255, 165, 0)  # Orange
    
    # Draw main box
    box_rect = p.Rect(box_x, box_y, box_width, box_height)
    p.draw.rect(screen, (245, 245, 245), box_rect)
    p.draw.rect(screen, color, box_rect, 4)
    
    # Draw title
    title_font = p.font.SysFont("Arial", 24, True)
    title_text = title_font.render("Game Over", True, (60, 60, 60))
    title_rect = title_text.get_rect(center=(box_x + box_width//2, box_y + 40))
    screen.blit(title_text, title_rect)
    
    # Draw main message
    message_font = p.font.SysFont("Arial", 28, True)
    message_text = message_font.render(text, True, color)
    message_rect = message_text.get_rect(center=(box_x + box_width//2, box_y + 100))
    screen.blit(message_text, message_rect)
    
    # Draw "Press any key to return" message
    return_font = p.font.SysFont("Arial", 16)
    return_text = return_font.render("Press any key to return to menu", True, (80, 80, 80))
    return_rect = return_text.get_rect(center=(box_x + box_width//2, box_y + 150))
    screen.blit(return_text, return_rect)

if __name__ == "__main__":
    main()
