import random
nextMove = None
pieceScore = {"K": 0, "Q": 9, "R": 5, "B": 3, "N": 3, "p": 1}

# ==================== PIECE POSITION EVALUATION TABLES ===================

knightScores = [[1, 1, 1, 1, 1, 1, 1, 1],
                [1, 2, 2, 2, 2, 2, 2, 1],
                [1, 2, 3, 3, 3, 3, 2, 1],
                [1, 2, 3, 4, 4, 3, 2, 1],
                [1, 2, 3, 4, 4, 3, 2, 1],
                [1, 2, 3, 3, 3, 3, 2, 1],
                [1, 2, 2, 2, 2, 2, 2, 1],
                [1, 1, 1, 1, 1, 1, 1, 1]]

bishopScores = [[4, 3, 2, 1, 1, 2, 3, 4],
                [3, 4, 3, 2, 2, 3, 4, 3],
                [2, 3, 4, 3, 3, 4, 3, 2],
                [1, 2, 3, 4, 4, 3, 2, 1],
                [1, 2, 3, 4, 4, 3, 2, 1],
                [2, 3, 4, 3, 3, 4, 3, 2],
                [3, 4, 3, 2, 2, 3, 4, 3],
                [4, 3, 2, 1, 1, 2, 3, 4]]

queenScores = [[1, 1, 1, 3, 1, 1, 1, 1],
               [1, 2, 3, 3, 3, 1, 1, 1],
               [1, 4, 3, 3, 3, 4, 2, 1],
               [1, 2, 3, 3, 3, 2, 2, 1],
               [1, 2, 3, 3, 3, 2, 2, 1],
               [1, 4, 3, 3, 3, 4, 2, 1],
               [1, 1, 2, 3, 3, 1, 1, 1],
               [1, 1, 1, 3, 1, 1, 1, 1]]

rookScores = [[4, 3, 4, 4, 4, 4, 3, 4],
              [4, 4, 4, 4, 4, 4, 4, 4],
              [1, 1, 2, 3, 3, 2, 1, 1],
              [1, 2, 3, 4, 4, 3, 2, 1],
              [1, 2, 3, 4, 4, 3, 2, 1],
              [1, 1, 2, 2, 2, 2, 1, 1],
              [4, 4, 4, 4, 4, 4, 4, 4],
              [4, 3, 2, 1, 1, 2, 3, 4]]

whitePawnScores = [[8, 8, 8, 8, 8, 8, 8, 8],
                   [8, 8, 8, 8, 8, 8, 8, 8],
                   [5, 6, 6, 7, 7, 6, 6, 5],
                   [2, 3, 3, 5, 5, 3, 3, 2],
                   [1, 2, 3, 4, 4, 3, 2, 1],
                   [1, 1, 2, 3, 3, 2, 1, 1],
                   [1, 1, 1, 0, 0, 1, 1, 1],
                   [0, 0, 0, 0, 0, 0, 0, 0]]

blackPawnScores = [[0, 0, 0, 0, 0, 0, 0, 0],
                   [1, 1, 1, 0, 0, 1, 1, 1],
                   [1, 1, 2, 3, 3, 2, 1, 1],
                   [1, 2, 3, 4, 4, 3, 2, 1],
                   [2, 3, 3, 5, 5, 3, 3, 2],
                   [5, 6, 6, 7, 7, 6, 6, 5],
                   [8, 8, 8, 8, 8, 8, 8, 8],
                   [8, 8, 8, 8, 8, 8, 8, 8]]


piecePositionScores = {"N": knightScores, "B": bishopScores, "Q": queenScores,
                       "R": rookScores, "wp": whitePawnScores, "bp": blackPawnScores}


# ======================== AI ALGORITHM CONFIGURATION ======================

CHECKMATE = 1000
STALEMATE = 0
DEPTH = 4

# Search tree tracking for visualization - REMOVED
current_search_id = 0


# \\\\\\\\\\\\\\\\\\\\\ AI ALGORITHM IMPLEMENTATIONS \\\\\\\\\\\\\\\\\\\\\\\

# ============================================================================
# ======================= RANDOM MOVE ALGORITHM ============================
# ============================================================================
def findRandomMoves(validMoves, thinking_queue=None, ai_info=None):
    index = random.randint(0, len(validMoves) - 1)
    selected = validMoves[index]
    
    # If this is a pawn promotion move, choose the promotion piece randomly
    # so AI doesn't always promote to a queen "as it always did before".
    try:
        if hasattr(selected, 'isPawnPromotion') and selected.isPawnPromotion:
            # choose from Queen, Rook, Bishop, Knight
            selected.promotion = random.choice(['Q', 'R', 'B', 'N'])
            if thinking_queue:
                thinking_queue.put(f"Selected promotion piece -> {selected.promotion}")
    except Exception:
        pass
    
    if thinking_queue:
        try:
            moves_str = ", ".join(str(m) for m in validMoves)
        except Exception:
            moves_str = str(validMoves)
        
        # Add structured thinking messages
        separator = "-" * 60
        thinking_queue.put(separator)
        
        if ai_info:
            thinking_queue.put(f"AI {ai_info['color']} [{ai_info['mode']}] is thinking...")
        else:
            thinking_queue.put("AI is thinking...")
            
        thinking_queue.put(f"Possible moves: [{moves_str}]")
        thinking_queue.put(f"Selected move of index [{index}] -> {selected}")
        thinking_queue.put(f"Selected move -> {selected}")
        thinking_queue.put(separator)
    
    return selected


# ============================================================================
# ==================== ALPHA-BETA PRUNING ALGORITHM ========================
# ============================================================================
def minimax(gs, depth, alpha, beta, maximizing_player, thinking_queue=None):
    # Check for terminal conditions
    if gs.board.is_checkmate():
        if gs.whiteToMove:
            return -CHECKMATE  # Black wins
        else:
            return CHECKMATE   # White wins
    elif gs.board.is_stalemate() or gs.board.is_insufficient_material() or gs.board.is_seventyfive_moves() or gs.board.is_fivefold_repetition():
        return STALEMATE
    
    if depth == 0:
        return scoreBoard(gs)
    
    if maximizing_player:
        max_eval = -CHECKMATE
        for move in gs.getValidMoves():
            gs.makeMove(move)
            eval_score = minimax(gs, depth - 1, alpha, beta, False, thinking_queue)
            gs.undoMove()
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Alpha-beta pruning
        return max_eval
    else:
        min_eval = CHECKMATE
        for move in gs.getValidMoves():
            gs.makeMove(move)
            eval_score = minimax(gs, depth - 1, alpha, beta, True, thinking_queue)
            gs.undoMove()
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha-beta pruning
        return min_eval


def scoreBoard(gs):
    """
    Score the board based on material and positional values
    Positive score favors white, negative score favors black
    """
    # Check for terminal conditions using python-chess board directly
    if gs.board.is_checkmate():
        if gs.whiteToMove:
            return -CHECKMATE  # Black wins
        else:
            return CHECKMATE   # White wins
    elif gs.board.is_stalemate() or gs.board.is_insufficient_material() or gs.board.is_seventyfive_moves() or gs.board.is_fivefold_repetition():
        return STALEMATE
    
    score = 0
    board_array = gs.get_board_array()  # Get 2D array representation
    
    for row in range(len(board_array)):
        for col in range(len(board_array[row])):
            square = board_array[row][col]
            if square != "--":
                # Material value
                piece_type = square[1]
                piece_value = pieceScore[piece_type]
                
                # Positional value
                positional_value = 0
                if piece_type == "p":
                    if square[0] == "w":
                        positional_value = whitePawnScores[row][col]
                    else:
                        positional_value = blackPawnScores[row][col]
                elif piece_type in piecePositionScores:
                    positional_value = piecePositionScores[piece_type][row][col]
                
                total_value = piece_value + positional_value * 0.1
                
                if square[0] == "w":
                    score += total_value
                else:
                    score -= total_value
    
    return score


def findBestMoveAlphaBeta(gs, validMoves, thinking_queue=None, ai_info=None):
    """
    Find the best move using minimax with alpha-beta pruning
    """
    global nextMove, current_search_id
    nextMove = None
    current_search_id += 1
    
    if thinking_queue:
        separator = "-" * 60
        thinking_queue.put(separator)
        if ai_info:
            thinking_queue.put(f"AI {ai_info['color']} [Alpha-Beta] is analyzing...")
        else:
            thinking_queue.put("AI [Alpha-Beta] is analyzing...")
        thinking_queue.put(f"Analyzing {len(validMoves)} possible moves at depth {DEPTH}")
    
    # Save the original player before the loop (critical fix)
    player_is_white = gs.whiteToMove
    
    # Start minimax with alpha-beta pruning
    best_move = None
    best_score = -CHECKMATE if player_is_white else CHECKMATE
    
    for move in validMoves:
        gs.makeMove(move)
        score = minimax(gs, DEPTH - 1, -CHECKMATE, CHECKMATE, 
                       not player_is_white, thinking_queue)
        gs.undoMove()
        
        # Use original player perspective, not the flipped gs.whiteToMove
        if player_is_white:
            if score > best_score:
                best_score = score
                best_move = move
        else:
            if score < best_score:
                best_score = score
                best_move = move
                
        if thinking_queue:
            thinking_queue.put(f"Move {move}: Score = {score}")
    
    if thinking_queue:
        thinking_queue.put(f"Best move selected: {best_move} (Score: {best_score})")
        thinking_queue.put(separator)
    
    nextMove = best_move
    return best_move


def findBestMove(gs, validMoves, returnQueue, ai_algorithms=None, thinking_queue=None, ai_info=None):
    global nextMove
    nextMove = None
    
    # Use the algorithm specified by ai_info mode (user selection)
    use_alpha_beta = False  # Default to random
    
    if ai_info and 'mode' in ai_info:
        if ai_info['mode'].lower() in ['alpha-beta']:
            use_alpha_beta = True
        elif ai_info['mode'].lower() in ['random']:
            use_alpha_beta = False
    
    # Execute the selected algorithm
    if use_alpha_beta:
        nextMove = findBestMoveAlphaBeta(gs, validMoves, thinking_queue, ai_info)
    else:
        nextMove = findRandomMoves(validMoves, thinking_queue, ai_info)
    
    returnQueue.put(nextMove)
