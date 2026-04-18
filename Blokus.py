# Blokus recreation
# 16 April 2026

import pygame
pygame.init()

# typedef
Point = tuple[int, int]
Color = tuple[int, int, int] | int

""" --- Edit game contraints (below) --- """

NUM_PLAYERS       = 3    # Supports 1 to 4 players
GRID_SIZE         = 20   # Standard board is 20x20 cells

MAX_SCREEN_WIDTH  = 900  # Measured in pixels
MAX_SCREEN_HEIGHT = 600

SCROLL_SPEED      = 5    # Scroll up/down to see all pieces, speed in pixels at 60 fps

""" ^^^ STOP EDITING ^^^ """

# Globals and constexpr
CELL_SIZE = int(min(MAX_SCREEN_WIDTH / (GRID_SIZE + 12.5), MAX_SCREEN_HEIGHT / (GRID_SIZE + 5)))

CELL_BORDER = 2 # shaved off right and bottom side
BOARD_OFFSET = int(2.5 * CELL_SIZE)
UI_OFFSET = int(2*BOARD_OFFSET + GRID_SIZE*CELL_SIZE)

SCREEN_WIDTH = int(CELL_SIZE * (GRID_SIZE + 12.5))
SCREEN_HEIGHT = int(CELL_SIZE * (GRID_SIZE + 5))

# Colors
WHITE = (255, 255, 255)
GREY  = (200, 200, 200)
BLACK = (0, 0, 0)

BLUE   = ( 24, 123, 222)
RED    = (222,  22,  29)
YELLOW = (224, 220,  29)
GREEN  = ( 12, 176,  42)

# Create the Blokus shapes, name -> list of coordinates relative to center
SHAPES = {
    'I1': [[0, 0]],
    'I2': [[0, 0], [1, 0]],
    'I3': [[-1, 0], [0, 0], [1, 0]],
    'V3': [[0, 0], [1, 0], [0, 1]],

    'I4': [[-1, 0], [0, 0], [1, 0], [2, 0]],
    'L4': [[0, 0], [0, 1], [1, 0], [2, 0]],
    'O4': [[0, 0], [1, 0], [0, 1], [1, 1]],
    'Z4': [[-1, 0], [0, 0], [0, 1], [1, 1]],
    'T4': [[-1, 0], [0, 0], [0, 1], [1, 0]],
    
    'I5': [[-2, 0], [-1, 0], [0, 0], [1, 0], [2, 0]],
    'L5': [[-1, 1], [-1, 0], [0, 0], [1, 0], [2, 0]],
    'P5': [[-1, 1], [-1, 0], [0, 0], [0, 1], [1, 0]],
    'T5': [[-1, 1], [-1, -1], [-1, 0], [0, 0], [1, 0]],
    'V5': [[-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]],
    'N5': [[-1, 1], [0, 1], [0, 0], [1, 0], [2, 0]],
    'W5': [[-1, 1], [-1, 0], [0, 0], [0, -1], [1, -1]],
    'Z5': [[-1, 1], [-1, 0], [0, 0], [1, 0], [1, -1]],
    'F5': [[0, 1], [-1, 0], [0, 0], [1, 0], [1, -1]],
    'X5': [[0, 0], [0, 1], [1, 0], [-1, 0], [0, -1]],
    'U5': [[0, 0], [-1, 0], [-1, 1], [1, 0], [1, 1]],
    'Y5': [[-1, 0], [0, 0], [0, 1], [1, 0], [2, 0]]
}


""" --- Handle the game pieces --- """
class Piece:
    
    __slots__ = ('name', 'shape', 'color', 'player_id', 'dragging', 'pos')

    def __init__(self, name, shape, color, player_id):
        self.name:      str         = name
        self.shape:     list[Point] = shape # List of (x, y) offsets, unit=cells
        self.color:     Color       = color
        self.player_id: int         = player_id
        self.dragging:  bool        = False
        self.pos:       list[int]   = [0, 0] # Screen position, in pixels

    def get_board_coords(self, screen_pos) -> list[Point]:
        bx = (screen_pos[0] - BOARD_OFFSET) // CELL_SIZE
        by = (screen_pos[1] - BOARD_OFFSET) // CELL_SIZE
        return [(bx + dx, by + dy) for dx, dy in self.shape]

    def draw(self, surface, pos=None) -> None:
        draw_pos = pos if pos else self.pos
        
        if draw_pos[0] < -3*CELL_SIZE or draw_pos[0] > SCREEN_WIDTH+3*CELL_SIZE or draw_pos[1] < -3*CELL_SIZE or draw_pos[1] > SCREEN_HEIGHT+3*CELL_SIZE:
            return
        
        for dx, dy in self.shape:
            pygame.draw.rect(surface, self.color, (draw_pos[0] + dx * CELL_SIZE, draw_pos[1] + dy * CELL_SIZE, CELL_SIZE - CELL_BORDER, CELL_SIZE - CELL_BORDER))


""" --- Blokus game board --- """

class BlokusGame:

    __slots__ = ('screen', 'clock', 'board', 'turn', 'players_pieces', 'selected_piece', 'draw_piece_offset', 'max_piece_offset')

    PLAYER_COLOR = { 0: GREY, 1: BLUE, 2: RED, 3: GREEN, 4: YELLOW }

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.board = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.turn = 1 # 1 for Blue, 2 for Red
        
        self.players_pieces = {
            p_id : [Piece(n, s, BlokusGame.PLAYER_COLOR[p_id], p_id) for n, s in SHAPES.items()]
            for p_id in range(1, NUM_PLAYERS + 1)
        }
        
        self.selected_piece = None
        self.draw_piece_offset = 0
        self.max_piece_offset = 0
        
        self.setup_piece_positions(self.turn)

    def setup_piece_positions(self, player: int) -> None:
        y_offset = BOARD_OFFSET
        for piece in self.players_pieces[player]:
            heights = sorted([pos[1] for pos in piece.shape])
            piece.pos = [UI_OFFSET, y_offset - heights[0]*CELL_SIZE]
            height = heights[-1] - heights[0] + 1
            y_offset += height*CELL_SIZE + CELL_SIZE // 2
        self.max_piece_offset = max(0, y_offset - SCREEN_HEIGHT + BOARD_OFFSET)

    def is_valid_move(self, piece, coords):
        has_diagonal = False

        for x, y in coords:
            # 1. Stay on board
            if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE): return False
            # 2. No overlapping
            if self.board[y][x] != 0: return False
            
            # 3. Check adjacents (Cannot touch same color side-to-side)
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and self.board[ny][nx] == piece.player_id:
                    return False
            
            # 4. Check diagonals (Must touch at least one same color corner)
            for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and self.board[ny][nx] == piece.player_id:
                    has_diagonal = True
        
        # Special rule: First move must touch a corner of the board
        if sum(row.count(piece.player_id) for row in self.board) == 0:
            corners = [(0,0), (0,19), (19,0), (19,19)]
            return any(c in coords for c in corners)

        return has_diagonal


    def run(self):
        running = True
        while running:
            self.screen.fill(WHITE)
            self.draw_board()
            self.draw_ui()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        break
                    
                    """ --- Rotate and Flip the piece --- """
                    
                    # r -> Rotate clockwise :: (x, y) -> (-y, x)
                    if event.key == pygame.K_r:
                        if self.selected_piece:
                            for pos in self.selected_piece.shape:
                                pos[0], pos[1] = -pos[1], pos[0]

                    # f -> Flip/Mirror :: (x, y) -> (x, -y)
                    if event.key == pygame.K_f:
                        if self.selected_piece:
                            for pos in self.selected_piece.shape:
                                pos[1] = -pos[1]
                    
                    # ARROW KEYS / WASD to rotate/flip
                    
                    # UP / w -> Flip vertically :: (x, y) -> (x, -y)
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        if self.selected_piece:
                            for pos in self.selected_piece.shape:
                                pos[1] = -pos[1]
                    # DOWN / s -> Flip horizontally :: (x, y) -> (-x, y)
                    if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        if self.selected_piece:
                            for pos in self.selected_piece.shape:
                                pos[0] = -pos[0]
                    # RIGHT / d -> Rotate CW :: (x, y) -> (-y, x)
                    if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        if self.selected_piece:
                            for pos in self.selected_piece.shape:
                                pos[0], pos[1] = -pos[1], pos[0]
                    # LEFT / a -> Rotate CCW :: (x, y) -> (y, -x)
                    if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        if self.selected_piece:
                            for pos in self.selected_piece.shape:
                                pos[0], pos[1] = pos[1], -pos[0]

                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    my += self.draw_piece_offset
                    
                    # Check which piece was clicked on
                    if mx < UI_OFFSET - BOARD_OFFSET: continue
                    
                    for piece in self.players_pieces[self.turn]:
                        for (dx, dy) in piece.shape:
                            px = piece.pos[0] + dx * CELL_SIZE
                            py = piece.pos[1] + dy * CELL_SIZE
                            if px <= mx <= px + CELL_SIZE and py <= my <= py + CELL_SIZE:
                                self.selected_piece = piece
                                piece.dragging = True
                                break
                        if self.selected_piece: break

                if event.type == pygame.MOUSEBUTTONUP:
                    if self.selected_piece:
                        coords = self.selected_piece.get_board_coords(event.pos)
                        if self.is_valid_move(self.selected_piece, coords):
                            for x, y in coords:
                                self.board[y][x] = self.selected_piece.player_id
                            self.players_pieces[self.turn].remove(self.selected_piece)
                            self.turn = (self.turn % NUM_PLAYERS) + 1  # 1 -> 2 -> 3 -> 4 -> 1

                        self.selected_piece.dragging = False
                        self.selected_piece = None
                        self.setup_piece_positions(self.turn) # Reset unused pieces positions

            mx, my = pygame.mouse.get_pos()
            
            if self.selected_piece:    
                self.selected_piece.pos = [mx - CELL_SIZE // 2, my - CELL_SIZE // 2]
            if mx >= UI_OFFSET and my >= SCREEN_HEIGHT-BOARD_OFFSET:
                self.draw_piece_offset = min(self.max_piece_offset, self.draw_piece_offset + SCROLL_SPEED)
                self.draw_ui()
            if mx >= UI_OFFSET and my <= BOARD_OFFSET:
                self.draw_piece_offset = max(0, self.draw_piece_offset - SCROLL_SPEED)
                self.draw_ui()

            pygame.display.flip()
            self.clock.tick(60)
        self.stats()

    def draw_board(self):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = pygame.Rect(BOARD_OFFSET + x * CELL_SIZE, BOARD_OFFSET + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, GREY, rect, width=1)
                if self.board[y][x] != 0:
                    pygame.draw.rect(self.screen, BlokusGame.PLAYER_COLOR[self.board[y][x]], rect.inflate(-2, -2))
    
    def draw_ui(self):
        # Draw remaining pieces for both players
        for piece in self.players_pieces[self.turn]:
            x, y = piece.pos[0], piece.pos[1] - self.draw_piece_offset
            piece.draw(self.screen, pos=[x, y] if not piece.dragging else None)

    def stats(self):
        for i in range(1, NUM_PLAYERS + 1):
            pts = sum(len(piece.shape) for piece in self.players_pieces[i])
            print(f"Player {i} had {pts} points remaining")

# TODO: skip button if no moves
if __name__ == "__main__":
    game = BlokusGame()
    game.run()
    pygame.quit()
