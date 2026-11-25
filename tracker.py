import json
import os
import argparse
import requests
from datetime import datetime
from tabulate import tabulate
import csv

watchlist_path = "watchlist.json"
def load_watchlist():  
    # Treat an empty file as uninitialized to avoid JSONDecodeError on fresh setups
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

def fetch_game_deals(game_name):
    # Custom User-Agent avoids default python-requests blocks on public APIs
    headers = {"User-Agent": "Steam Deal Tracker/1.0"}
    headers = {"User-Agent": "Steam Deal Tracker/1.0"}
    base_url = "https://www.cheapshark.com/api/1.0/games"
    search_result = requests.get(base_url, params={"title": game_name}, headers=headers)
    search_result.raise_for_status()
    results = search_result.json()
    if not results:
        return None
    game_id = results[0]["gameID"]
    current_price = float(results[0]["cheapest"])
    # CheapShark's title search only returns gameID and current price,
    # so a second lookup by ID is required to fetch the all-time historical low.
    detail_res = requests.get(f"https://www.cheapshark.com/api/1.0/games?id={game_id}", headers=headers)
    detail_res.raise_for_status()
    details = detail_res.json()
    historical_low = float(details["cheapestPriceEver"]["price"])
    # CheapShark returns cheapestPriceEver.date as a Unix epoch timestamp
    historical_low_date = datetime.fromtimestamp(details["cheapestPriceEver"]["date"]).strftime("%Y-%m-%d")
    return {
        "name": game_name,
        "current_price": current_price,
        "historical_low": historical_low,
        "historical_low_date": historical_low_date,
    }

def send_discord_alert(deal_info, target_price, webhook_url):
    if deal_info["current_price"] <= target_price:
        message = {
            "content": f"Deal Alert! {deal_info['name']} is now ${deal_info['current_price']:.2f}, which is below your target price of ${target_price:.2f}!"
        }
        try:
            response = requests.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to send Discord alert for {deal_info['name']}: {e}")

def log_price_history(deal_info, target_price, status, csv_path="price_history.csv"):
    # Check if the file is new or empty so headers are only written once
    file_exists = os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Game", "Current Price", "Target Price", "Historical Low", "Historical Low Date", "Status"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            deal_info["name"],
            f"${deal_info['current_price']:.2f}",
            f"${target_price:.2f}",
            f"${deal_info['historical_low']:.2f}",
            deal_info["historical_low_date"],
            status,
        ])

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
        if not watchlist["games"]:
            print("No games in the watchlist to check.")
            return
        # Load webhook from environment variable so secret URLs aren't committed to GitHub
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        table_rows = []
        for game in watchlist["games"]:
            deal_info = fetch_game_deals(game["name"])
            if deal_info is None:
                print(f"No deals found for {game['name']}.")
                continue
            if webhook_url:
                send_discord_alert(deal_info, game["target_price"], webhook_url)
            status = "Buy Now!" if deal_info["current_price"] <= game["target_price"] else "Wait"
            log_price_history(deal_info, game["target_price"], status)
            table_rows.append([
                deal_info["name"],
                f"${deal_info['current_price']:.2f}",
                f"${deal_info['historical_low']:.2f}",
                deal_info["historical_low_date"],
                status,
            ])
        if table_rows:
            print(tabulate(table_rows, headers=["Game", "Current Price", "Historical Low", "Historical Low Date", "Status"], tablefmt="grid"))
    
if __name__ == "__main__":
    main()

