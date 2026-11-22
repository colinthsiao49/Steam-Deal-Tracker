import json
import os
import argparse


watchlist_path = "watchlist.json"
def load_watchlist():  
    if not os.path.exists(watchlist_path) or os.path.getsize(watchlist_path) == 0:
        data = {
            "games": [],
            "events": {
                "Spring Sale": "03-14",
                "Summer Sale": "06-26",
                "Fall Sale": "11-25",
                "Winter Sale": "12-19",
            },
        }
        save_watchlist(data)
        return data
    with open(watchlist_path, "r") as f:
        return json.load(f)

def save_watchlist(data):
    with open(watchlist_path, "w") as f:
        json.dump(data, f, indent=2)

def parse_args():
    parser = argparse.ArgumentParser(description="Track games and events.")
    parser.add_argument("--add-game", type=str, help="Add a game to the watchlist.")
    parser.add_argument("--target", type=float, help="Target price for the game being added.")
    parser.add_argument("--remove-game", type=str, help="Remove a game from the watchlist.")
    parser.add_argument("--list-games", action="store_true", help="List all games in the watchlist.")
    parser.add_argument("--list-events", action="store_true", help="List all events in the watchlist.")
    parser.add_argument("--check", action="store_true", help="Check live prices vs. historical lows.")
    return parser.parse_args()

def main():
    args = parse_args()
    watchlist = load_watchlist()

    if args.add_game:
        if args.target is None:
            print("Please provide a target price using --target.")
            return
        watchlist["games"].append({"name": args.add_game, "target_price": args.target})
        save_watchlist(watchlist)
        print(f"Added {args.add_game} with target price {args.target} to the watchlist.")

    elif args.remove_game:
        watchlist["games"] = [game for game in watchlist["games"] if game["name"] != args.remove_game]
        save_watchlist(watchlist)
        print(f"Removed {args.remove_game} from the watchlist.")

    elif args.list_games:
        print("Games in the watchlist:")
        for game in watchlist["games"]:
            print(f"- {game['name']} (Target Price: {game['target_price']})")

    elif args.list_events:
        print("Events in the watchlist:")
        for event, date in watchlist["events"].items():
            print(f"- {event}: {date}")

    elif args.check:
        # Placeholder for checking live prices vs. historical lows
        print("Checking live prices vs. historical lows... (functionality not implemented)")
    
if __name__ == "__main__":
    main()