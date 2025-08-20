import chess
import chess.pgn

class GameState():
    def __init__(self):
        # Use python-chess board
        self.board = chess.Board()
        
        # Keep track of move history for our GUI
        self.moveLog = []
        
        # GUI-specific settings
        self.playerWantsToPlayAsBlack = False
        
        # Game state flags
        self.checkmate = False
        self.stalemate = False
        
        # For compatibility with existing GUI code
        self.whiteToMove = self.board.turn  # True for white, False for black
        
    def makeMove(self, move):
        """Make a move on the board"""
        # Convert our custom move to python-chess move
        chess_move = self._convert_to_chess_move(move)
        
        if chess_move in self.board.legal_moves:
            # Store the move in our log
            self.moveLog.append(move)
            
            # Make the move on python-chess board
            self.board.push(chess_move)
            
            # Update turn
            self.whiteToMove = self.board.turn
            
            # Update game state flags
            self._update_game_state()
        
    def undoMove(self):
        """Undo the last move"""
        if len(self.moveLog) > 0:
            # Remove from our log
            self.moveLog.pop()
            
            # Undo on python-chess board
            if len(self.board.move_stack) > 0:
                self.board.pop()
                
            # Update turn
            self.whiteToMove = self.board.turn
            
            # Reset game state flags
            self.checkmate = False
            self.stalemate = False
    
    def getValidMoves(self):
        """Get all valid moves for current player"""
        moves = []
        
        # Get legal moves from python-chess
        legal_moves = list(self.board.legal_moves)
        
        # Convert to our move format
        for chess_move in legal_moves:
            move = self._convert_from_chess_move(chess_move)
            moves.append(move)
            
        return moves
    
    def copy(self):
        """Create a deep copy of the game state for simulations"""
        new_gs = GameState()
        new_gs.board = self.board.copy()
        new_gs.moveLog = self.moveLog.copy()
        new_gs.playerWantsToPlayAsBlack = self.playerWantsToPlayAsBlack
        new_gs.checkmate = self.checkmate
        new_gs.stalemate = self.stalemate
        new_gs.whiteToMove = self.whiteToMove
        return new_gs
    
    def get_board_array(self):
        """Convert python-chess board to 2D array for GUI compatibility"""
        board_array = []
        
        # Create 8x8 array
        for rank in range(8):
            row = []
            for file in range(8):
                square = chess.square(file, 7-rank)  # Convert coordinates
                piece = self.board.piece_at(square)
                
                if piece is None:
                    row.append("--")
                else:
                    # Convert to our piece notation (e.g., 'wK', 'bp')
                    color = 'w' if piece.color == chess.WHITE else 'b'
                    piece_type = piece.symbol().upper()
                    if piece_type == 'P':
                        piece_type = 'p'
                    row.append(color + piece_type)
            board_array.append(row)
            
        return board_array
    
    def _convert_to_chess_move(self, custom_move):
        """Convert our custom move format to python-chess move"""
        start_square = chess.square(custom_move.startCol, 7 - custom_move.startRow)
        end_square = chess.square(custom_move.endCol, 7 - custom_move.endRow)
        
        # Handle promotion
        promotion = None
        # Prefer an explicit promotion attribute if present (set by AI),
        # otherwise fall back to the isPawnPromotion flag (default to queen).
        if hasattr(custom_move, 'promotion') and custom_move.promotion:
            promo = custom_move.promotion
            if isinstance(promo, str):
                promo = promo.upper()
                if promo == 'Q':
                    promotion = chess.QUEEN
                elif promo == 'R':
                    promotion = chess.ROOK
                elif promo == 'B':
                    promotion = chess.BISHOP
                elif promo == 'N':
                    promotion = chess.KNIGHT
        elif hasattr(custom_move, 'isPawnPromotion') and custom_move.isPawnPromotion:
            promotion = chess.QUEEN

        return chess.Move(start_square, end_square, promotion)
    
    def _convert_from_chess_move(self, chess_move):
        """Convert python-chess move to our custom move format"""
        start_row = 7 - chess.square_rank(chess_move.from_square)
        start_col = chess.square_file(chess_move.from_square)
        end_row = 7 - chess.square_rank(chess_move.to_square)
        end_col = chess.square_file(chess_move.to_square)
        
        # Create move with current board state
        board_array = self.get_board_array()
        move = Move((start_row, start_col), (end_row, end_col), board_array)
        
        # Set special move flags
        move.castle = self.board.is_castling(chess_move)
        move.isEnpassantMove = self.board.is_en_passant(chess_move)
        
        # Check for pawn promotion
        if chess_move.promotion:
            move.isPawnPromotion = True
            # Map python-chess promotion back to a simple symbol for GUI/AI
            if chess_move.promotion == chess.QUEEN:
                move.promotion = 'Q'
            elif chess_move.promotion == chess.ROOK:
                move.promotion = 'R'
            elif chess_move.promotion == chess.BISHOP:
                move.promotion = 'B'
            elif chess_move.promotion == chess.KNIGHT:
                move.promotion = 'N'
            
        return move
    
    def _update_game_state(self):
        """Update checkmate and stalemate flags"""
        if self.board.is_checkmate():
            self.checkmate = True
        elif self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            self.stalemate = True
    
    def getBoardString(self):
        """Get board state as string for draw detection"""
        return str(self.board)
    
    @property
    def whiteKinglocation(self):
        """Get white king location for compatibility"""
        king_square = self.board.king(chess.WHITE)
        if king_square is not None:
            rank = 7 - chess.square_rank(king_square)
            file = chess.square_file(king_square)
            return (rank, file)
        return None
    
    @property
    def blackKinglocation(self):
        """Get black king location for compatibility"""
        king_square = self.board.king(chess.BLACK)
        if king_square is not None:
            rank = 7 - chess.square_rank(king_square)
            file = chess.square_file(king_square)
            return (rank, file)
        return None


class Move():
    """Move class for compatibility with existing GUI"""
    
    # Chess notation mappings
    ranksToRows = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
    rowsToRanks = {value: key for key, value in ranksToRows.items()}
    filesToCols = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
    colsToFiles = {value: key for key, value in filesToCols.items()}
    
    def __init__(self, startSquare, endSquare, board, isEnpassantMove=False, castle=False):
        self.startRow = startSquare[0]
        self.startCol = startSquare[1]
        self.endRow = endSquare[0]
        self.endCol = endSquare[1]
        
        # Get piece information
        self.pieceMoved = board[self.startRow][self.startCol]
        
        # Handle captured piece
        if isEnpassantMove:
            # For en passant, captured pawn is on starting row
            self.pieceCaptured = board[self.startRow][self.endCol]
        else:
            self.pieceCaptured = board[self.endRow][self.endCol]
            
        # Set move properties
        self.castle = castle
        self.isEnpassantMove = isEnpassantMove
        self.isCapture = self.pieceCaptured != '--'
        
        # Generate unique move ID
        self.moveID = self.startRow * 1000 + self.startCol * 100 + self.endRow * 10 + self.endCol
        
        # Check for pawn promotion
        self.isPawnPromotion = self._check_pawn_promotion()
    
    def _check_pawn_promotion(self):
        """Check if this move is a pawn promotion"""
        if self.pieceMoved[1] == 'p':  # It's a pawn
            if (self.pieceMoved[0] == 'w' and self.endRow == 0) or \
               (self.pieceMoved[0] == 'b' and self.endRow == 7):
                return True
        return False
    
    def __eq__(self, other):
        """Check if two moves are equal"""
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False
    
    def getRankFile(self, row, col):
        """Convert row, col to chess notation"""
        return self.colsToFiles[col] + self.rowsToRanks[row]
    
    def __str__(self):
        """String representation of the move"""
        if self.castle:
            return "O-O" if self.endCol == 6 else "O-O-O"
        
        start_square = self.getRankFile(self.startRow, self.startCol)
        end_square = self.getRankFile(self.endRow, self.endCol)
        
        if self.pieceMoved[1] == 'p':  # Pawn move
            if self.isCapture:
                return start_square + "x" + end_square
            else:
                return end_square
        else:  # Piece move
            piece_symbol = self.pieceMoved[1].upper()
            if piece_symbol == 'P':
                piece_symbol = ''
            
            if self.isCapture:
                return piece_symbol + "x" + end_square
            else:
                return piece_symbol + end_square


# For backward compatibility, create castleRights class
class castleRights():
    def __init__(self, wks, wqs, bks, bqs):
        self.wks = wks
        self.wqs = wqs
        self.bks = bks
        self.bqs = bqs
