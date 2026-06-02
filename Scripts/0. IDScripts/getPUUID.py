from riotwatcher import RiotWatcher

# Use RiotWatcher (not LolWatcher) for account IDs
rw = RiotWatcher("RGAPI-5d61bb4a-3913-4c74-99b8-5ab54a3879b4")

# For ME1 (Seed with your ME account)
me_acc = rw.account.by_riot_id("europe", "b3do", "1804")
print(f"ME PUUID: {me_acc['puuid']}")

# For EUW (Seed with your EU account)
eu_acc = rw.account.by_riot_id("europe", "manga", "420")
print(f"EU PUUID: {eu_acc['puuid']}")