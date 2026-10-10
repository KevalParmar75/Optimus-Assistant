"""
Standalone Demo Script for Laya Local Decision Agent with Real Browser Execution
Run: python demo_laya_agent.py
"""
import time, sys, os
from tools.laya_engine import LayaEngine
from agents.browser_agent import BrowserAgent

def run_demo():
    print("=" * 65)
    print(" [LAYA LOCAL DECISION AGENT -- REAL BROWSER EXECUTION DEMO]")
    print(" 100% Offline Decision Engine + Real Chrome Automation")
    print("=" * 65)

    print("\n[1/2] Initializing Laya Decision Engine & Bumblebee Browser Agent...")
    t0 = time.time()
    laya = LayaEngine.get_instance()
    browser_agent = BrowserAgent()
    load_time = (time.time() - t0) * 1000
    print(f"[OK] Ready in {load_time:.1f}ms\n")

    print("=" * 65)
    print("--- REAL-TIME INTERACTIVE BROWSER TESTER ---")
    print("Try commands like:")
    print("  • 'play sharmeeli on youtube'")
    print("  • 'search google for modernbert benchmark'")
    print("  • 'open https://github.com'")
    print("Type 'exit' or 'q' to quit.")
    print("=" * 65)

    while True:
        try:
            user_input = input("\nOptimus-Laya > ").strip()
            if not user_input or user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting demo agent. Goodbye!")
                break

            t_start = time.time()
            
            # Step 1: Fast Laya routing & decision
            routed_agent = laya.route_supervisor_agent(user_input)
            action_decided = laya.choose_browser_action(user_input)
            t_decision = (time.time() - t_start) * 1000

            print(f"  |- Laya Decision : Agent={routed_agent.upper()} | Action={action_decided} ({t_decision:.1f} ms)")

            # Step 2: Real Browser Execution if routed to browser/chat
            if routed_agent in ["browser", "chat"]:
                print(f"  |- Executing Real Browser Action...")
                exec_result = browser_agent.execute_plan(user_input)
                print(f"  |- Execution Result: {exec_result}")
            else:
                print(f"  |- [Simulated] Routed to {routed_agent.upper()} agent.")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting demo agent.")
            break

if __name__ == "__main__":
    run_demo()
