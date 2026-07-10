import json
import random
import time
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

# ---------- Configuration & System Constants ----------
QUIZ_FILE = "quiz.json"
SCORE_DB = "quiz_scores.db"
TOTAL_QUESTIONS_PER_SESSION = 15

# ---------- Database Architecture Layer ----------
class ScoreRepository:
    """Handles thread-safe database interactions for persistence of session scores."""
    
    def __init__(self, db_path: str = SCORE_DB):
        self.db_path = db_path
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Initializes database schemas using production indices for rapid ordering queries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    total INTEGER NOT NULL,
                    correct_count INTEGER NOT NULL,
                    difficulty TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Index created on score to prevent full table scans during ranking retrieval
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_quiz_scores_ranking ON quiz_scores (score DESC)'
            )
            conn.commit()

    def save(self, player: str, score: int, total: int, correct: int, difficulty: str) -> None:
        """Persists a verified player performance record to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quiz_scores (player, score, total, correct_count, difficulty)
                VALUES (?, ?, ?, ?, ?)
            ''', (player, score, total, correct, difficulty))
            conn.commit()

    def get_top_rankings(self, limit: int = 10) -> List[Tuple[Any, ...]]:
        """Retrieves targeted slice of highly ranked profiles by descending score metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT player, score, total, correct_count, difficulty, created_at
                FROM quiz_scores 
                ORDER BY score DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()


# ---------- Core Engine Components ----------
class QuizBank:
    """Manages full life-cycle validation, seeding, and filtration of question data models."""
    
    def __init__(self, file_path: str = QUIZ_FILE):
        self.file_path = file_path

    def load_or_seed(self) -> List[Dict[str, Any]]:
        """Guarantees a set of valid operational questions by seeding defaults if file missing."""
        if not os.path.exists(self.file_path):
            default_dataset = self._generate_default_bank()
            with open(self.file_path, 'w', encoding='utf-8') as stream:
                json.dump(default_dataset, stream, indent=4, ensure_ascii=False)
            return default_dataset

        try:
            with open(self.file_path, 'r', encoding='utf-8') as stream:
                return json.load(stream)
        except (json.JSONDecodeError, IOError) as err:
            print(f"❌ Critical system failure decoding questions: {err}")
            return []

    def _generate_default_bank(self) -> List[Dict[str, Any]]:
        """Constructs an integrated base questions dataset covering multiple domains."""
        return [
            # Python Domain - Easy
            {"category": "Python", "difficulty": "Easy", "question": "What is the output of print(2**3)?", "options": ["6", "8", "9", "4"], "answer": 1},
            {"category": "Python", "difficulty": "Easy", "question": "Which keyword is used to define a function?", "options": ["def", "function", "define", "func"], "answer": 0},
            {"category": "Python", "difficulty": "Easy", "question": "What is the correct file extension for Python files?", "options": [".py", ".pt", ".pyt", ".pyth"], "answer": 0},
            {"category": "Python", "difficulty": "Easy", "question": "Which of the following is a native Python data type?", "options": ["int", "integer", "number", "num"], "answer": 0},
            {"category": "Python", "difficulty": "Easy", "question": "How do you instantiate a float primitive set to 2.8?", "options": ["x = 2.8", "x = float(2.8)", "Both frameworks work", "None of these"], "answer": 2},
            # Python Domain - Medium
            {"category": "Python", "difficulty": "Medium", "question": "What is the syntactical structure used to define a list literal?", "options": ["(list)", "[list]", "{list}", "<list>"], "answer": 1},
            {"category": "Python", "difficulty": "Medium", "question": "Which core data structure collections represent mutable identities?", "options": ["Tuple", "String", "List", "Int"], "answer": 2},
            {"category": "Python", "difficulty": "Medium", "question": "What is the explicit evaluation output of: 'Hello' + 'World'?", "options": ["HelloWorld", "Hello World", "Hello+World", "TypeErrorException"], "answer": 0},
            {"category": "Python", "difficulty": "Medium", "question": "Which operational method handles target elements removal from lists?", "options": ["remove()", "delete()", "pop()", "Both remove() and pop()"], "answer": 3},
            {"category": "Python", "difficulty": "Medium", "question": "What primary operational lifecycle role does '__init__' implement?", "options": ["Object Constructor Initialization", "Resource Destructor Scope", "Main Runtime Routine Entry", "Direct Memory Allocation"], "answer": 0},
            # Python Domain - Hard
            {"category": "Python", "difficulty": "Hard", "question": "What is the theoretical worst-case time complexity of an optimized Binary Search algorithm?", "options": ["O(n)", "O(log n)", "O(n^2)", "O(1)"], "answer": 1},
            {"category": "Python", "difficulty": "Hard", "question": "What is the evaluations expression outcome of: print(True + True)?", "options": ["2", "True", "1", "TypeError"], "answer": 0},
            {"category": "Python", "difficulty": "Hard", "question": "What design architectural construct defines a modern decorator pattern implementation?", "options": ["Higher-order wrapper modifying targeting callables", "Scoped volatile local reference", "Explicit polymorphic subtype", "Isolated dynamic namespace layer"], "answer": 0},
            {"category": "Python", "difficulty": "Hard", "question": "Contrast comparative behavioral states between logical operators '==' and 'is':", "options": ["Value Equivalence vs Memory Reference Address Identity", "Memory Identity Profile vs Abstract Struct Equivalence", "Identical contextual compiler outputs", "Compiler directives optimizations only"], "answer": 0},
            # General Domain - Easy
            {"category": "General Knowledge", "difficulty": "Easy", "question": "What is the capital city of India?", "options": ["Mumbai", "New Delhi", "Kolkata", "Chennai"], "answer": 1},
            {"category": "General Knowledge", "difficulty": "Easy", "question": "Identify the globally largest oceanic body on Earth:", "options": ["Atlantic Ocean", "Indian Ocean", "Pacific Ocean", "Arctic Ocean"], "answer": 2},
            {"category": "General Knowledge", "difficulty": "Easy", "question": "Which planet inside our stellar system is distinctively named the Red Planet?", "options": ["Venus", "Mars", "Jupiter", "Saturn"], "answer": 1},
            {"category": "General Knowledge", "difficulty": "Easy", "question": "What is the complete count of geological continents present on Earth?", "options": ["5", "6", "7", "8"], "answer": 2},
            {"category": "General Knowledge", "difficulty": "Easy", "question": "Which sovereign territory spans the globally largest contiguous land area surface?", "options": ["Russia", "China", "United States", "Canada"], "answer": 0},
            # General Domain - Medium
            {"category": "General Knowledge", "difficulty": "Medium", "question": "Which metalloid component forms the structural bedrock base for solar photovoltaic cells?", "options": ["Silicon", "Carbon", "Iron", "Copper"], "answer": 0},
            {"category": "General Knowledge", "difficulty": "Medium", "question": "What is the correct elemental atomic abbreviation notation for Gold?", "options": ["Au", "Ag", "Fe", "Cu"], "answer": 0},
            {"category": "General Knowledge", "difficulty": "Medium", "question": "Which municipal administration officially hosted the Tokyo 2020 Olympiad?", "options": ["Japan", "China", "United States", "United Kingdom"], "answer": 0},
            {"category": "General Knowledge", "difficulty": "Medium", "question": "Which historical innovator secured the primary foundational patent tracking for the Telephone?", "options": ["Alexander Graham Bell", "Thomas Edison", "Nikola Tesla", "Albert Einstein"], "answer": 0},
            # General Domain - Hard
            {"category": "General Knowledge", "difficulty": "Hard", "question": "What was the estimated nominal macroeconomic GDP scaling metrics benchmark for the USA in 2024?", "options": ["~28 Trillion USD", "~22 Trillion USD", "~25 Trillion USD", "~30 Trillion USD"], "answer": 0},
            {"category": "General Knowledge", "difficulty": "Hard", "question": "Which terrestrial land mammal retains documented peak track speed capabilities?", "options": ["Cheetah", "Pronghorn Antelope", "Bengal Tiger", "Quarter Horse"], "answer": 0},
        ]


class InputController:
    """Provides non-blocking I/O routines using daemon tracking monitors."""

    @staticmethod
    def _timeout_monitor(kill_signal: List[bool], duration: float) -> None:
        """Background thread target that registers a expiration trigger after specified sleep interval."""
        time.sleep(duration)
        kill_signal[0] = True

    @classmethod
    def capture_with_deadline(cls, prompt: str, seconds_limit: float, default_value: str = "") -> Tuple[str, bool]:
        """Intercepts interactive console inputs, breaking execution if duration constraints breach."""
        expiration_flag = [False]
        monitor_worker = threading.Thread(
            target=cls._timeout_monitor, 
            args=(expiration_flag, seconds_limit),
            daemon=True
        )
        monitor_worker.start()

        try:
            user_input = input(prompt)
            # If input finishes right after background expiration register checks
            if expiration_flag[0]:
                return default_value, True
            return user_input, False
        except (KeyboardInterrupt, SystemExit, Exception):
            return default_value, True


# ---------- Application Orchestrator ----------
class QuizApplication:
    """Main operational workflow controller processing quiz setup, mechanics execution, and analytics."""

    def __init__(self) -> None:
        self.repository = ScoreRepository()
        self.bank_manager = QuizBank()
        self.difficulty_configurations = {
            "1": {"tier": "Easy", "time_limit": 10.0, "weight": 1},
            "2": {"tier": "Medium", "time_limit": 7.0, "weight": 2},
            "3": {"tier": "Hard", "time_limit": 5.0, "weight": 3}
        }

    def _select_operational_tier(self) -> Tuple[str, float, int]:
        """Renders explicit interactive prompt configuration choices for execution metrics."""
        print("\n" + "═"*60)
        print(" 🎯 SYSTEM RUNTIME OPTIONS: SELECT DIFFICULTY CONTROLLER")
        print("═"*60)
        for identifier, metadata in self.difficulty_configurations.items():
            print(f"  [{identifier}] {metadata['tier']:-<10} (Limit: {int(metadata['time_limit'])}s / Scaling Weight: x{metadata['weight']})")
        
        user_selection = input("\nEnter system route identity (1/2/3): ").strip()
        config = self.difficulty_configurations.get(user_selection)
        
        if not config:
            print("\n⚠️ Selection validation mismatch. Automatically allocating: 'Easy'")
            return "Easy", 10.0, 1
        return config["tier"], config["time_limit"], config["weight"]

    def execute_session(self) -> None:
        """Orchestrates operational sequence flows tracking active telemetry scoring states."""
        all_questions = self.bank_manager.load_or_seed()
        if not all_questions:
            print("❌ Failed initialization sequence. System questions pool empty.")
            return

        tier_name, seconds_limit, point_weight = self._select_operational_tier()

        # Isolate targets filtered down matching explicit operational tiers
        filtered_pool = [q for q in all_questions if q.get("difficulty", "Easy") == tier_name]
        
        # Guard clause verifying capacity constraints
        if len(filtered_pool) < 5:
            print(f"\n⚠️ Available question profile count low for layer: {tier_name}. Implementing generic fallback mix.")
            filtered_pool = list(all_questions)

        random.shuffle(filtered_pool)
        session_workload = filtered_pool[:TOTAL_QUESTIONS_PER_SESSION]
        
        total_questions = len(session_workload)
        accumulated_score = 0
        successful_answers_count = 0
        
        print("\n" + "═"*60)
        print(f" 🚀 INITIALIZING INSTANCE MODULE | CONFIG: {tier_name.upper()} RUNTIME")
        print(f" 📝 Profile Allocation: {total_questions} Questions | Deadline Scope: {int(seconds_limit)}s/Item")
        print("═"*60)
        input("\nPress [Enter] to activate pipeline threads...")

        session_start_marker = time.perf_counter()

        for position, packet in enumerate(session_workload, 1):
            print("\n" + "─"*60)
            print(f" 📂 Question Context: [{position}/{total_questions}] | Category: {packet.get('category')}")
            print("─"*60)
            print(f"\n👉 {packet['question']}\n")

            for option_idx, display_option in enumerate(packet['options'], 1):
                print(f"   ({option_idx}) {display_option}")

            print(f"\n⏱️ Awaiting terminal entry [Deadline limit: {int(seconds_limit)}s]...")

            question_start_marker = time.perf_counter()
            terminal_capture, did_expire = InputController.capture_with_deadline("\nResponse Interface Index (1-4): ", seconds_limit)
            question_end_marker = time.perf_counter()

            if did_expire:
                print(f"\n⏰ Execution Deadline Breached! Skipping downstream pipeline item.")
                print(f"💡 Target Valid Baseline was: {packet['options'][packet['answer']]}")
                continue

            cleaned_input = terminal_capture.strip()
            if cleaned_input.isdigit() and 1 <= int(cleaned_input) <= 4:
                parsed_index = int(cleaned_input) - 1
                
                if parsed_index == packet['answer']:
                    item_duration = question_end_marker - question_start_marker
                    # Dynamic programmatic velocity reward processing
                    velocity_bonus = max(0, int((seconds_limit - item_duration) / 1.5))
                    calculated_points = point_weight + velocity_bonus
                    
                    accumulated_score += calculated_points
                    successful_answers_count += 1
                    print(f"\n✅ Verification Success! Allocation: +{calculated_points} Units (Bonus Acceleration weight: +{velocity_bonus})")
                else:
                    print(f"\n❌ Verification Mismatch. Target Option was: {packet['options'][packet['answer']]}")
            else:
                print(f"\n⚠️ Input parse structure error. Target baseline fallback was: {packet['options'][packet['answer']]}")

        session_end_marker = time.perf_counter()
        total_elapsed_duration = session_end_marker - session_start_marker
        accuracy_percentage = (successful_answers_count / total_questions) * 100 if total_questions > 0 else 0.0

        print("\n" + "═"*60)
        print(" 🏁 STRUCTURAL EVALUATION SEQUENCE TERMINATED")
        print("═"*60)
        print(f"\n📊 Performance Matrix Summary:")
        print(f"   • Net Identifiers Verified : {successful_answers_count}/{total_questions}")
        print(f"   • Gross Point Metrics      : {accumulated_score} Points")
        print(f"   • Total Active Execution   : {total_elapsed_duration:.2f} Seconds")
        print(f"   • Process Accuracy Ratio   : {accuracy_percentage:.1f}%")

        self._render_motivational_feedback(accuracy_percentage)

        player_identity = input("\nEnter profile system handle for logs (Default: Anonymous): ").strip() or "Anonymous"
        self.repository.save(player_identity, accumulated_score, total_questions, successful_answers_count, tier_name)

        self._display_historical_leaderboard()

    @staticmethod
    def _render_motivational_feedback(accuracy: float) -> None:
        """Determines feedback tiers based on execution accuracy boundaries."""
        if accuracy == 100.0:
            print("\n🌟 UNCAUGHT EXCEPTIONAL METRIC: PERFECT COMPILER MATRIX! 🏆")
        elif accuracy >= 75.0:
            print("\n👍 Highly efficient operation metrics tracking. Keep scaling! 💪")
        elif accuracy >= 50.0:
            print("\n📖 Performance bounds balanced. Optimize focus strategies! 📚")
        else:
            print("\n🤔 Low density optimization levels detected. Re-index base layers! 🔧")

    def _display_historical_leaderboard(self) -> None:
        """Queries and formats globally tracked telemetry scoring performance matrices."""
        print("\n" + "═"*60)
        print(" 🏆 SECURED TOP TELEMETRY TRACKING RECORDS")
        print("═"*60)

        historical_records = self.repository.get_top_rankings(limit=10)
        if historical_records:
            for rank, (player, score, total, correct, diff, date_stamp) in enumerate(historical_records, 1):
                trophy_badge = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"[{rank}]"
                formatted_date = date_stamp[:16] if date_stamp else "N/A"
                print(f"  {trophy_badge:-<4} Profile: {player:<12} | Yield: {score:<4} pts ({correct}/{total} hits) | Tier: [{diff}] | Registered: {formatted_date}")
        else:
            print(" No diagnostic session records found. System data tracking stack clear.")
        print("\n" + "═"*60)


# ---------- Main Processing Entry Hook ----------
if __name__ == "__main__":
    try:
        app_instance = QuizApplication()
        app_instance.execute_session()
    except KeyboardInterrupt:
        print("\n\n⚠️ System processing sequence interrupted by user signal directive. Shutting down runtime instances...")
